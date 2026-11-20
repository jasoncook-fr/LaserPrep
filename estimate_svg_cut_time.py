#!/usr/bin/env python3
"""Experimental best-effort time estimator for LaserPrep SVG output.

This tool is deliberately independent of LaserPrep production processing.
It measures simple SVG path geometry and applies provisional empirical rates.
Unsupported SVG commands/metadata never prevent a partial estimate.

Defaults: 60W, CB-2mm, optimization ON.
"""
from __future__ import annotations
import argparse
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_MACHINE = "60W"
DEFAULT_MATERIAL = "Carton bois 2mm"
# Provisional whole-job-derived rates, not validated operation rates.
CUT_SECONDS_PER_M = {"60W": 21.2, "100W": 21.1}
VECTOR_ENGRAVE_SECONDS_PER_M = {"60W": 36.0, "100W": 31.4}
FILL_SECONDS_PER_1000_MM2 = {"60W": 12.865, "100W": 15.503}
FILL_INTERCEPT = {"60W": 21.48, "100W": 34.40}
COLORS = {"blue": (0, 0, 255), "green": (0, 255, 0), "red": (255, 0, 0), "black": (0, 0, 0)}
TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")

def color_name(value):
    if not value: return None
    v=value.strip().lower()
    if v in ("none","transparent"): return None
    if v in ("blue","#00f","#0000ff","rgb(0,0,255)"): return "blue"
    if v in ("green","#0f0","#00ff00","rgb(0,255,0)"): return "green"
    if v in ("red","#f00","#ff0000","rgb(255,0,0)"): return "red"
    if v in ("black","#000","#000000","rgb(0,0,0)"): return "black"
    if v.startswith("#") and len(v)==4:
        v="#"+"".join(ch*2 for ch in v[1:])
    if v.startswith("#") and len(v)==7:
        try:
            rgb=tuple(int(v[i:i+2],16) for i in (1,3,5))
            return next((n for n,c in COLORS.items() if c==rgb),None)
        except ValueError: pass
    return None

def cubic(p0,p1,p2,p3,t):
    u=1-t
    return (u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
            u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1])

def parse_path(d):
    """Flatten SVG M/L/C/Z path data; returns subpaths and approximate length."""
    tokens=TOKEN.findall(d or "")
    subpaths=[]; current=[]; pos=(0.0,0.0); start=None; cmd=None; i=0; total=0.0
    def add(pt):
        nonlocal total,pos,current
        if current: total+=math.dist(pos,pt)
        current.append(pt); pos=pt
    while i<len(tokens):
        if tokens[i].isalpha(): cmd=tokens[i]; i+=1
        if cmd is None: break
        if cmd in ("Z","z"):
            if current and start:
                total+=math.dist(pos,start); current.append(start)
                subpaths.append(current); current=[]; pos=start
            cmd=None; continue
        rel=cmd.islower(); c=cmd.upper()
        try:
            if c=="M":
                x,y=float(tokens[i]),float(tokens[i+1]); i+=2
                pt=(x+pos[0],y+pos[1]) if rel else (x,y)
                if current: subpaths.append(current); current=[]
                pos=pt; start=pt; current=[pt]; cmd="l" if rel else "L"
            elif c=="L":
                x,y=float(tokens[i]),float(tokens[i+1]); i+=2
                add((x+pos[0],y+pos[1]) if rel else (x,y))
            elif c=="C":
                vals=list(map(float,tokens[i:i+6])); i+=6
                p0=pos
                p1=(vals[0]+p0[0],vals[1]+p0[1]) if rel else (vals[0],vals[1])
                p2=(vals[2]+p0[0],vals[3]+p0[1]) if rel else (vals[2],vals[3])
                p3=(vals[4]+p0[0],vals[5]+p0[1]) if rel else (vals[4],vals[5])
                prev=p0
                for k in range(1,21):
                    pt=cubic(p0,p1,p2,p3,k/20)
                    total+=math.dist(prev,pt); current.append(pt); prev=pt
                pos=p3
            else:
                # Unsupported command: skip the rest of this path rather than crash.
                return subpaths,total,False
        except (IndexError,ValueError):
            return subpaths,total,False
    if current: subpaths.append(current)
    return subpaths,total,True

def polygon_area(points):
    if len(points)<3: return 0.0
    if points[0]!=points[-1]: points=points+[points[0]]
    return abs(sum(points[i][0]*points[i+1][1]-points[i+1][0]*points[i][1] for i in range(len(points)-1))/2)

def filename_metadata(name):
    n=name.lower()
    machine="100W" if "100w" in n else "60W"
    material="Carton bois 2mm"
    m=re.search(r"(?:cb|carton\s*bois)[-_ ]?(\d+(?:\.\d+)?)\s*mm",n)
    if m: material=f"Carton bois {m.group(1)}mm"
    opt="OFF" if re.search(r"opt(?:imization|imisation)?[-_ ]?off|opt[-_ ]?off",n) else "ON"
    return machine,material,opt

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("svg",type=Path)
    ap.add_argument("--machine",choices=("60W","100W"))
    ap.add_argument("--material")
    ap.add_argument("--optimization",choices=("ON","OFF"))
    args=ap.parse_args()
    warnings=[]
    machine,material,opt=filename_metadata(args.svg.name)
    if args.machine: machine=args.machine
    else: warnings.append(f"Machine not identified in filename; defaulted to {machine}.")
    if args.material: material=args.material
    elif material=="Carton bois 2mm": warnings.append("Material/thickness not identified; defaulted to Carton bois 2mm.")
    if args.optimization: opt=args.optimization
    else: warnings.append(f"Optimization setting inferred as {opt} (filename heuristic/default).")
    blue=green=red=fill_area=0.0; unsupported=0; paths=0
    try:
        root=ET.parse(args.svg).getroot()
        for el in root.iter():
            if el.tag.split("}")[-1]!="path": continue
            d=el.get("d","")
            if not d: continue
            style={}
            if el.get("style"):
                for pair in el.get("style","").split(";"):
                    if ":" in pair:
                        k,v=pair.split(":",1); style[k.strip()]=v.strip()
            stroke=el.get("stroke",style.get("stroke"))
            fill=el.get("fill",style.get("fill"))
            sc=color_name(stroke); fc=color_name(fill)
            sub, length, ok=parse_path(d)
            paths+=1
            if not ok: unsupported+=1
            if sc=="blue": blue+=length
            elif sc in ("green","red"): 
                if sc=="green": green+=length
                else: red+=length
            # Approximate fill area from flattened contours. Restrict to solid black fill.
            if fc=="black":
                fill_area+=sum(polygon_area(s) for s in sub)
    except Exception as e:
        warnings.append(f"SVG read/parse problem: {e}; partial estimate may be zero.")
    cut=blue/1000*CUT_SECONDS_PER_M[machine]
    engrave=(green+red)/1000*VECTOR_ENGRAVE_SECONDS_PER_M[machine]
    filled=fill_area/1000*FILL_SECONDS_PER_1000_MM2[machine]+(FILL_INTERCEPT[machine] if fill_area>0 else 0)
    total=cut+engrave+filled
    print("\nEXPERIMENTAL LASERPREP SVG TIME ESTIMATE")
    print("="*44)
    print(f"File:          {args.svg.name}")
    print(f"Machine:       {machine}")
    print(f"Material:      {material}")
    print(f"Optimization:  {opt}")
    print(f"SVG paths:     {paths} (unsupported path commands: {unsupported})")
    print(f"Blue cut:      {blue:,.1f} mm -> {cut:.1f} s")
    print(f"Green vector:  {green:,.1f} mm")
    print(f"Red vector:    {red:,.1f} mm -> {(green+red)/1000*VECTOR_ENGRAVE_SECONDS_PER_M[machine]:.1f} s combined")
    print(f"Black fill:    {fill_area:,.1f} mm² -> {filled:.1f} s")
    print("-"*44)
    print(f"BEST-EFFORT ESTIMATE: {total:.1f} seconds ({total/60:.2f} minutes)")
    print("\nAssumptions/warnings:")
    for w in warnings: print("- "+w)
    print("- Provisional vector rates derived from production-job observations, not isolated controlled tests.")
    print("- Blue is treated as cutting; green/red as vector engraving; black filled paths as filled engraving.")
    print("- Filled-area estimate uses the experimental filled-engraving model.")
    print("- This is an experimental estimate only; optimization/material thickness do not yet adjust the model.")
    print("- Geometry length is approximate; cubic Beziers sampled at 20 steps.")
if __name__=="__main__": main()
