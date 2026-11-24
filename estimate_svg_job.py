#!/usr/bin/env python3
"""Experimental real-SVG estimator (approximate geometry; review warnings)."""
import argparse, math, re, xml.etree.ElementTree as ET
from pathlib import Path
from integrated_time_estimator import fill_model, cut_rate

TOK=re.compile(r"[MmLlHhVvCcSsQqTtZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
def path_length(d):
    toks=TOK.findall(d or "");i=0;cmd=None;cur=(0.,0.);start=cur;prev_ctrl=None;length=0.;pts=[]
    def num():
        nonlocal i
        v=float(toks[i]);i+=1;return v
    def add(p):
        nonlocal cur,length
        length+=math.hypot(p[0]-cur[0],p[1]-cur[1]);cur=p;pts.append(p)
    while i<len(toks):
        if toks[i].isalpha():cmd=toks[i];i+=1
        if not cmd:break
        c=cmd.upper();rel=cmd.islower()
        if c=="Z":add(start);cur=start;cmd=None;prev_ctrl=None;continue
        if c in ("M","L"):
            x,y=num(),num();p=(x+cur[0],y+cur[1]) if rel else (x,y)
            if c=="M":cur=p;start=p;pts.append(p);cmd="l" if rel else "L"
            else:add(p)
            prev_ctrl=None
        elif c=="H":
            x=num();add((cur[0]+x if rel else x,cur[1]));prev_ctrl=None
        elif c=="V":
            y=num();add((cur[0],cur[1]+y if rel else y));prev_ctrl=None
        elif c in ("C","S","Q","T"):
            if c=="C":
                vals=[num() for _ in range(6)];p1,p2,p3=(vals[0],vals[1]),(vals[2],vals[3]),(vals[4],vals[5])
            elif c=="S":
                vals=[num() for _ in range(4)];p1=(2*cur[0]-prev_ctrl[0],2*cur[1]-prev_ctrl[1]) if prev_ctrl else cur;p2,p3=(vals[0],vals[1]),(vals[2],vals[3])
            elif c=="Q":
                vals=[num() for _ in range(4)];p1,p3=(vals[0],vals[1]),(vals[2],vals[3]);p2=None
            else:
                vals=[num() for _ in range(2)];p1=(2*cur[0]-prev_ctrl[0],2*cur[1]-prev_ctrl[1]) if prev_ctrl else cur;p3=(vals[0],vals[1]);p2=None
            if rel:
                base=cur
                p1=(p1[0]+base[0],p1[1]+base[1]);p3=(p3[0]+base[0],p3[1]+base[1])
                if p2 is not None:p2=(p2[0]+base[0],p2[1]+base[1])
            old=cur
            for k in range(1,31):
                t=k/30;u=1-t
                if c in ("C","S"):
                    p=(u**3*old[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*old[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1])
                else:p=(u*u*old[0]+2*u*t*p1[0]+t*t*p3[0],u*u*old[1]+2*u*t*p1[1]+t*t*p3[1])
                add(p)
            prev_ctrl=p2 if c in ("C","S") else p1
        else:
            raise ValueError("Unsupported path command (likely arc); path parsing stopped.")
    return length,pts

def style(el):
    s=el.attrib.get("style","");st=dict(x.split(":",1) for x in s.split(";") if ":" in x)
    return el.attrib.get("stroke",st.get("stroke","none")).strip().lower(),el.attrib.get("fill",st.get("fill","none")).strip().lower()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("svg");p.add_argument("--machine",choices=("60W","100W"),required=True)
    p.add_argument("--speed",choices=("100%","50%"),default="100%");p.add_argument("--scan",choices=("Normal","Left-to-right"),default="Normal")
    p.add_argument("--jct",choices=("ON","OFF"),default="ON");p.add_argument("--overhead-sec",type=float,default=120)
    p.add_argument("--vector-sec-per-m",type=float,default=None);a=p.parse_args()
    root=ET.parse(a.svg).getroot();totals={k:0. for k in ("blue","green","red","black")};counts={k:0 for k in totals};fill_bbox_area=0;fills=0;warnings=[]
    for el in root.iter():
        tag=el.tag.split("}")[-1];stroke,fill=style(el)
        if tag=="path" and el.attrib.get("d"):
            length,pts=path_length(el.attrib["d"])
            cat={"#0000ff":"blue","blue":"blue","rgb(0,0,255)":"blue","#00ff00":"green","green":"green","rgb(0,255,0)":"green","#ff0000":"red","red":"red","rgb(255,0,0)":"red","#000000":"black","black":"black","rgb(0,0,0)":"black"}.get(stroke)
            if cat:totals[cat]+=length;counts[cat]+=1
            if fill not in ("none","transparent") and pts:
                xs=[q[0] for q in pts];ys=[q[1] for q in pts];fill_bbox_area+=max(0,(max(xs)-min(xs))*(max(ys)-min(ys)));fills+=1
        if "transform" in el.attrib:warnings.append("Transform attributes detected; not applied.")
    if root.attrib.get("viewBox"):warnings.append("viewBox detected: SVG-unit-to-mm scaling is not applied.")
    cut=totals["blue"];vector=totals["green"]+totals["red"];rate=cut_rate(a.machine,"JcT "+a.jct);cut_sec=cut*rate if rate else 0
    vr=a.vector_sec_per_m if a.vector_sec_per_m is not None else (25 if a.machine=="60W" else 29);vec_sec=vector/1000*vr
    fm=fill_model(a.machine,a.speed,a.scan);fill_sec=max(0,fm[0]*fill_bbox_area+fm[1]) if fills and fm else 0
    total=cut_sec+vec_sec+fill_sec+a.overhead_sec
    print("\nLASERPREP — REAL SVG EXPERIMENTAL ESTIMATE");print("="*55);print("File:",Path(a.svg).name);print(f"Machine: {a.machine} | JcT {a.jct}")
    print("Path length totals (SVG units; scale not applied):")
    for k in totals:print(f"  {k}: {totals[k]:,.1f} ({counts[k]} paths)")
    print(f"Cut estimate: {cut_sec:.1f}s; vector estimate: {vec_sec:.1f}s at {vr:.1f} s/m")
    print(f"Filled paths: {fills}; sum of bounding-box areas: {fill_bbox_area:.1f} SVG-unit²; fill estimate: {fill_sec:.1f}s")
    print(f"Overhead: {a.overhead_sec:.1f}s");print("-"*55);print(f"TOTAL ESTIMATE: {total:.1f}s ({total/60:.2f} min)")
    print("WARNING: rough color mapping; black paths excluded; bounding-box fill area is not true area.")
    print("Path commands outside M/L/H/V/C/S/Q/T/Z (e.g. elliptical arcs) are unsupported.")
    for w in set(warnings):print("WARNING:",w)
if __name__=="__main__":main()
