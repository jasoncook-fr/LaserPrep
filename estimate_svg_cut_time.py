#!/usr/bin/env python3
"""Experimental best-effort time estimator for LaserPrep SVG output."""
from __future__ import annotations
import argparse, math, re
import xml.etree.ElementTree as ET
from pathlib import Path

CUT_SECONDS_PER_M = {"60W": 21.2, "100W": 21.1}
VECTOR_ENGRAVE_SECONDS_PER_M = {"60W": 36.0, "100W": 31.4}
FILL_SECONDS_PER_1000_MM2 = {"60W": 12.865, "100W": 15.503}
FILL_INTERCEPT = {"60W": 21.48, "100W": 34.40}
COLORS = {"blue": (0,0,255), "green": (0,255,0), "red": (255,0,0), "black": (0,0,0)}
TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")

def color_name(value):
    if not value: return None
    v=value.strip().lower()
    if v in ("none","transparent"): return None
    named={"blue":"blue","green":"green","red":"red","black":"black"}
    if v in named: return named[v]
    if v.startswith("#") and len(v)==4: v="#"+"".join(ch*2 for ch in v[1:])
    if v.startswith("#") and len(v)==7:
        try:
            rgb=tuple(int(v[i:i+2],16) for i in (1,3,5))
            return next((n for n,c in COLORS.items() if c==rgb),None)
        except ValueError: pass
    m=re.fullmatch(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",v)
    if m:
        rgb=tuple(map(int,m.groups()))
        return next((n for n,c in COLORS.items() if c==rgb),None)
    return None

def cubic(p0,p1,p2,p3,t):
    u=1-t
    return (u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
            u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1])

def parse_path(d):
    """Flatten supported M/L/C/Z commands; identify the first unsupported command."""
    tokens=TOKEN.findall(d or "")
    subpaths=[]; current=[]; pos=(0.,0.); start=None; cmd=None; i=0; total=0.
    def add(pt):
        nonlocal total,pos,current
        if current: total+=math.dist(pos,pt)
        current.append(pt); pos=pt
    while i<len(tokens):
        if tokens[i].isalpha(): cmd=tokens[i]; i+=1
        if cmd is None: break
        if cmd in ("Z","z"):
            if current and start:
                total+=math.dist(pos,start); current.append(start); subpaths.append(current); current=[]; pos=start
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
                    pt=cubic(p0,p1,p2,p3,k/20); total+=math.dist(prev,pt); current.append(pt); prev=pt
                pos=p3
            else: return subpaths,total,False,c
        except (IndexError,ValueError): return subpaths,total,False,c
    if current: subpaths.append(current)
    return subpaths,total,True,None

def polygon_area(points):
    if len(points)<3: return 0.
    if points[0]!=points[-1]: points=points+[points[0]]
    return abs(sum(points[i][0]*points[i+1][1]-points[i+1][0]*points[i][1] for i in range(len(points)-1))/2)

def filename_metadata(name):
    n=name.lower()
    machine_match=re.search(r"(60|100)\s*w",n)
    machine=machine_match.group(1)+"W" if machine_match else None
    thickness=re.search(r"(?:cb|carton\s*bois)[-_ ]?(\d+(?:[.,]\d+)?)\s*(?:mm)?",n)
    material=f"Carton bois {thickness.group(1).replace(',', '.') }mm" if thickness else None
    opt_match=re.search(r"opt(?:imization|imisation)?[-_ ]?(on|off)|opt[-_ ]?(on|off)",n)
    opt=opt_match.group(1).upper() if opt_match else None
    return machine,material,opt

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("svg",type=Path); ap.add_argument("--machine",choices=("60W","100W"))
    ap.add_argument("--material"); ap.add_argument("--optimization",choices=("ON","OFF"))
    args=ap.parse_args(); warnings=[]
    fm,mat,fo=filename_metadata(args.svg.name)
    machine=args.machine or fm or "60W"
    material=args.material or mat or "Carton bois 2mm"
    opt=args.optimization or fo or "ON"
    if not args.machine and not fm: warnings.append("Machine not identified; defaulted to 60W.")
    if not args.material and not mat: warnings.append("Material/thickness not identified; defaulted to Carton bois 2mm.")
    if not args.optimization and not fo: warnings.append("Optimization not identified; defaulted to ON.")
    blue=green=red=fill_area=0.; paths=unsupported=0
    bad_by_color={}; bad_commands={}
    try:
        root=ET.parse(args.svg).getroot()
        for el in root.iter():
            if el.tag.split("}")[-1]!="path": continue
            d=el.get("d","")
            if not d: continue
            style={}
            for pair in el.get("style","").split(";"):
                if ":" in pair:
                    k,v=pair.split(":",1); style[k.strip()]=v.strip()
            sc=color_name(el.get("stroke",style.get("stroke")))
            fc=color_name(el.get("fill",style.get("fill")))
            sub,length,ok,bad=parse_path(d); paths+=1
            if not ok:
                unsupported+=1; key=sc or fc or "unclassified"
                bad_by_color[key]=bad_by_color.get(key,0)+1
                bad_commands[bad]=bad_commands.get(bad,0)+1
            if sc=="blue": blue+=length
            elif sc=="green": green+=length
            elif sc=="red": red+=length
            if fc=="black": fill_area+=sum(polygon_area(s) for s in sub)
    except Exception as e: warnings.append(f"SVG read/parse problem: {e}")
    cut=blue/1000*CUT_SECONDS_PER_M[machine]
    green_time=green/1000*VECTOR_ENGRAVE_SECONDS_PER_M[machine]
    red_time=red/1000*VECTOR_ENGRAVE_SECONDS_PER_M[machine]
    filled=fill_area/1000*FILL_SECONDS_PER_1000_MM2[machine]+(FILL_INTERCEPT[machine] if fill_area>0 else 0)
    total=cut+green_time+red_time+filled
    print("\nEXPERIMENTAL LASERPREP SVG TIME ESTIMATE\n"+"="*44)
    print(f"File:          {args.svg.name}\nMachine:       {machine}\nMaterial:      {material}\nOptimization:  {opt}")
    print(f"SVG paths:     {paths} (unsupported: {unsupported})")
    print(f"Blue cutting:  {blue:,.1f} mm -> {cut:.1f} s ({cut/60:.2f} min)")
    print(f"Green vector:  {green:,.1f} mm -> {green_time:.1f} s ({green_time/60:.2f} min)")
    print(f"Red vector:    {red:,.1f} mm -> {red_time:.1f} s ({red_time/60:.2f} min)")
    print(f"Black fill:    {fill_area:,.1f} mm² -> {filled:.1f} s ({filled/60:.2f} min)")
    print("-"*44)
    print(f"BEST-EFFORT ESTIMATE: {total:.1f} seconds ({total/60:.2f} minutes)")
    if unsupported:
        print("\nINCOMPLETE GEOMETRY WARNING: estimate uses only supported portions of paths.")
        print("Unsupported command counts: "+", ".join(f"{k}: {v}" for k,v in sorted(bad_commands.items())))
        print("Affected paths by detected color: "+", ".join(f"{k}: {v}" for k,v in sorted(bad_by_color.items())))
    print("\nAssumptions/warnings:")
    for w in warnings: print("- "+w)
    print("- Provisional vector rates derived from production-job observations, not isolated controlled tests.")
    print("- Blue is treated as cutting; green/red as vector engraving; black filled paths as filled engraving.")
    print("- Filled-area estimate uses the experimental filled-engraving model.")
    print("- Optimization/material thickness currently do not adjust model rates.")
    print("- Cubic Beziers are sampled at 20 steps; transforms and other SVG complexities may not be accounted for.")
if __name__=="__main__": main()
