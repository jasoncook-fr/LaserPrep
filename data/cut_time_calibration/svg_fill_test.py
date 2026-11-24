#!/usr/bin/env python3
"""Experimental SVG fill geometry diagnostic. Does not modify SVGs or estimate laser runtime."""
from __future__ import annotations
import argparse, csv, re, sys
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"
PATH_COMMAND_RE = re.compile(r"[AaCcHhLlMmQqSsTtVvZz]")
NUMBER_RE = re.compile(r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?")

def local(tag):
    return tag.rsplit("}", 1)[-1]

def analyze(path: Path):
    root = ET.parse(path).getroot()
    counts = {}
    filled = 0
    fill_none = 0
    paths = 0
    path_commands = 0
    path_numbers = 0
    warnings = []
    fill_colors = set()
    transformed = 0
    unsupported_shapes = 0
    for el in root.iter():
        tag = local(el.tag)
        if tag in ("path", "rect", "circle", "ellipse", "polygon", "polyline"):
            counts[tag] = counts.get(tag, 0) + 1
            style = el.attrib.get("style", "")
            fill = el.attrib.get("fill")
            if fill is None and style:
                m = re.search(r"(?:^|;)\s*fill\s*:\s*([^;]+)", style)
                fill = m.group(1).strip() if m else None
            if fill is None:
                fill = "black"  # SVG default fill
            if fill.lower() == "none":
                fill_none += 1
            else:
                filled += 1
                fill_colors.add(fill)
            if "transform" in el.attrib:
                transformed += 1
            if tag == "path":
                paths += 1
                d = el.attrib.get("d", "")
                path_commands += len(PATH_COMMAND_RE.findall(d))
                path_numbers += len(NUMBER_RE.findall(d))
        elif tag in ("text", "image", "use", "clipPath", "mask", "filter"):
            unsupported_shapes += 1
    if transformed:
        warnings.append(f"{transformed} relevant elements have transforms; metrics are not normalized.")
    if unsupported_shapes:
        warnings.append(f"{unsupported_shapes} text/image/use/clip/mask/filter elements found; may affect rendering.")
    if not paths and filled:
        warnings.append("No SVG path elements found; filled primitive shapes only.")
    viewbox = root.attrib.get("viewBox", "")
    return {
        "file": str(path), "viewBox": viewbox, "filled_elements": filled,
        "fill_none_elements": fill_none, "path_count": paths,
        "path_commands": path_commands, "path_numeric_tokens": path_numbers,
        "shape_counts": ";".join(f"{k}:{v}" for k,v in sorted(counts.items())),
        "fill_values": ";".join(sorted(fill_colors)),
        "transformed_elements": transformed, "unsupported_elements": unsupported_shapes,
        "warnings": " | ".join(warnings),
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("svg_files", nargs="+", type=Path, help="SVG file(s)")
    ap.add_argument("--csv", type=Path, help="Optional CSV output path")
    args = ap.parse_args()
    rows=[]
    for p in args.svg_files:
        if not p.exists():
            print(f"ERROR: not found: {p}", file=sys.stderr)
            continue
        try:
            row=analyze(p)
            rows.append(row)
            print("\n"+p.name)
            print(f"  viewBox: {row['viewBox'] or '(not defined)'}")
            print(f"  filled SVG elements: {row['filled_elements']}")
            print(f"  fill='none' elements: {row['fill_none_elements']}")
            print(f"  paths: {row['path_count']} | path commands: {row['path_commands']} | numeric tokens: {row['path_numeric_tokens']}")
            print(f"  shapes: {row['shape_counts'] or '(none)'}")
            print(f"  fill values: {row['fill_values'] or '(none)'}")
            if row['warnings']:
                print("  WARN: "+row['warnings'])
            print("  NOTE: Diagnostic only; this does NOT calculate actual scanline/engraving distance or runtime.")
        except Exception as e:
            print(f"ERROR parsing {p}: {e}", file=sys.stderr)
    if args.csv and rows:
        fields=list(rows[0])
        args.csv.parent.mkdir(parents=True,exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        print(f"\nCSV written: {args.csv}")
    if not rows:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
