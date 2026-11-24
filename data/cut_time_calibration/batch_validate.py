#!/usr/bin/env python3
"""Batch validation for the provisional LaserPrep cut-time estimator."""

import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from math import cos, sin, radians

from svgpathtools import parse_path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from provisional_estimator import estimate

TEST_DIR = Path("/home/jaz/Nextcloud/LaserPrep/TMP/TIME_TEST_FILES")
OUTPUT = TEST_DIR / "validation_results.csv"
PT_TO_MM = 25.4 / 72.0

TIME_RE = re.compile(r"^(\d+)m(\d+)s")
MACHINE_RE = re.compile(r"(60W|100W)", re.I)
COLORS = {"blue": "#0000ff", "green": "#00ff00", "red": "#ff0000", "black": "#000000"}

def norm_color(value):
    if not value:
        return None
    value = value.strip().lower()
    if value in ("none", "transparent"):
        return None
    if value.startswith("#") and len(value) == 4:
        value = "#" + "".join(ch * 2 for ch in value[1:])
    return value

def parse_style(node):
    style = {}
    for item in node.attrib.get("style", "").split(";"):
        if ":" in item:
            k, v = item.split(":", 1)
            style[k.strip()] = v.strip()
    style.update(node.attrib)
    return style

def multiply(A, B):
    a,b,c,d,e,f = A
    g,h,i,j,k,l = B
    return (a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*l+e, b*k+d*l+f)

def matrix_transform(text):
    result = (1,0,0,1,0,0)
    for name, args in re.findall(r"([a-zA-Z]+)\s*\(([^)]*)\)", text or ""):
        v = [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]
        if name == "matrix" and len(v) == 6:
            m = tuple(v)
        elif name == "translate":
            m = (1,0,0,1,v[0],v[1] if len(v)>1 else 0)
        elif name == "scale":
            m = (v[0],0,0,v[1] if len(v)>1 else v[0],0,0)
        elif name == "rotate":
            angle = radians(v[0]); c,s = cos(angle),sin(angle)
            m = (c,s,-s,c,0,0)
            if len(v) >= 3:
                cx,cy = v[1:3]
                m = multiply((1,0,0,1,cx,cy),multiply(m,(1,0,0,1,-cx,-cy)))
        elif name == "skewX" and len(v)==1:
            from math import tan
            m = (1,0,tan(radians(v[0])),1,0,0)
        elif name == "skewY" and len(v)==1:
            from math import tan
            m = (1,tan(radians(v[0])),0,1,0,0)
        else:
            continue
        result = multiply(result, m)
    return result

def transformed_length(path, matrix, samples_per_segment=100):
    if matrix == (1,0,0,1,0,0):
        return path.length(error=1e-4) * PT_TO_MM
    a,b,c,d,e,f = matrix
    total = 0.0
    for segment in path:
        previous = None
        for i in range(samples_per_segment + 1):
            z = segment.point(i / samples_per_segment)
            current = complex(a*z.real+c*z.imag+e, b*z.real+d*z.imag+f)
            if previous is not None:
                total += abs(current-previous)
            previous = current
    return total * PT_TO_MM

def parse_svg(filename):
    root = ET.parse(filename).getroot()
    totals = {"blue":0.0,"green":0.0,"red":0.0,"black_fill_paths":0,"unsupported":0}

    def walk(node, inherited, parent_matrix):
        tag = node.tag.split("}",1)[-1]
        if tag in ("defs","clipPath","symbol"):
            return
        style = dict(inherited)
        style.update(parse_style(node))
        combined = multiply(parent_matrix, matrix_transform(node.attrib.get("transform","")))
        if tag == "path":
            dpath = node.attrib.get("d","")
            if dpath:
                try:
                    path = parse_path(dpath)
                    stroke = norm_color(style.get("stroke"))
                    fill = norm_color(style.get("fill", "black"))
                    if stroke in (COLORS["blue"], COLORS["green"], COLORS["red"]):
                        key = next(k for k,v in COLORS.items() if v == stroke and k != "black")
                        totals[key] += transformed_length(path, combined)
                    if fill == "#000000":
                        totals["black_fill_paths"] += 1
                except Exception as exc:
                    totals["unsupported"] += 1
                    print(f"PATH ERROR ({filename.name}): {exc}", file=sys.stderr)
        for child in node:
            walk(child, style, combined)
    walk(root, {}, (1,0,0,1,0,0))
    return totals

def main():
    rows = []
    for filename in sorted(TEST_DIR.glob("*.svg")):
        match = TIME_RE.match(filename.name)
        machine_match = MACHINE_RE.search(filename.name)
        if not match or not machine_match:
            print(f"SKIP: {filename.name}")
            continue
        actual = int(match.group(1))*60 + int(match.group(2))
        machine = machine_match.group(1).upper()
        geometry = parse_svg(filename)
        result = estimate(machine=machine, blue_straight_mm=geometry["blue"],
            blue_curves_mm=0, green_vector_mm=geometry["green"],
            red_vector_mm=geometry["red"], black_fill_area_mm2=0,
            overhead_seconds=120)
        predicted = result["total_seconds"]
        error = predicted-actual
        rows.append({"file":filename.name,"machine":machine,"actual_seconds":actual,
            "blue_length_mm":round(geometry["blue"],2),"green_length_mm":round(geometry["green"],2),
            "red_length_mm":round(geometry["red"],2),"black_fill_paths_unmeasured":geometry["black_fill_paths"],
            "unsupported_paths":geometry["unsupported"],"estimated_seconds":round(predicted,2),
            "estimated_minutes":result["rounded_minutes"],"error_seconds":round(error,2),
            "error_minutes":round(error/60,2),"error_percent":round(error/actual*100,2)})
        print(f"{filename.name:45} actual={actual:5d}s estimate={predicted:7.1f}s error={error:+7.1f}s")
    if not rows:
        print("No valid files found."); return
    with OUTPUT.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    errors=[r["error_seconds"] for r in rows]; abs_errors=[abs(e) for e in errors]
    print("\n"+"="*60); print(f"FILES TESTED: {len(rows)}")
    print(f"MEAN ERROR: {sum(errors)/len(errors):+.1f}s")
    print(f"MAE: {sum(abs_errors)/len(abs_errors):.1f}s")
    print(f"MAX ABS ERROR: {max(abs_errors):.1f}s")
    print(f"RESULTS: {OUTPUT}"); print("="*60)

if __name__ == "__main__":
    main()
