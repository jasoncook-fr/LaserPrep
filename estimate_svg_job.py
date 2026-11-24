#!/usr/bin/env python3
"""Experimental estimator that accepts a real SVG and reports geometry-based estimate.

SVG parsing is intentionally conservative: handles basic path commands (M/L/H/V,
C/S/Q/T/Z), samples curves, categorizes common laser colors, approximates filled
area from bounding boxes (NOT true area), and warns about unsupported transforms.
"""
import argparse, math, re, xml.etree.ElementTree as ET
from pathlib import Path
from integrated_time_estimator import fill_model, cut_rate

TOK=re.compile(r"[MmLlHhVvCcSsQqTtZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
def path_length(d):
    toks=TOK.findall(d or ""); i=0; cmd=None; cur=(0.,0.); start=cur; prev_ctrl=None; length=0.; pts=[]
    def num(): 
        nonlocal i
        v=float(toks[i]); i+=1; return v
    def add(p):
        nonlocal cur,length
        length+=math.hypot(p[0]-cur[0],p[1]-cur[1]);cur=p;pts.append(p)
    while i<len(toks):
        if toks[i].isalpha():cmd=toks[i];i+=1
        if not cmd:break
        c=cmd.upper(); rel=cmd.islower()
        if c=="Z": add(start);cur=start;cmd=None;continue
        if c=="M" or c=="L":
            x,y=num(),num();p=(x+cur[0],y+cur[1]) if rel else (x,y)
            if c=="M":cur=p;start=p;pts.append(p);cmd="l" if rel else "L"
            else:add(p)
        elif c=="H":
            x=num();add((cur[0]+x if rel else x,cur[1]))
        elif c=="V":
            y=num();add((cur[0],cur[1]+y if rel else y))
        elif c in ("C","S","Q","T"):
            if c=="C": vals=[num() for _ in range(6)]; p1,p2,p3=(vals[0],vals[1]),(vals[2],vals[3]),(vals[4],vals[5])
                # 
            elif c=="S": vals=[num() for _ in range(4)];p1=(2*cur[0]-prev_ctrl[0],2*cur[1]-prev_ctrl[1]) if prev_ctrl else cur;p2,p3=(vals[0],vals[1]),(vals[2],vals[3])
            elif c=="Q": vals=[num() for _ in range(4)];p1,p3=(vals[0],vals[1]),(vals[2],vals[3]);p2=None
            else: vals=[num() for _ in range(2)];p1=(2*cur[0]-prev_ctrl[0],2*cur[1]-prev_ctrl[1]) if prev_ctrl else cur;p3=(vals[0],vals[1]);p2=None
            if rel:
                if c in ("C","S"):p1=(p1[0]+cur[0],p1[1]+cur[1]);p2=(p2[0]+cur[0],p2[1]+cur[1]);p3=(p3[0]+cur[0],p3[1]+cur[1])
                else:p1=(p1[0]+cur[0],p1[1]+cur[1]);p3=(p3[0]+cur[0],p3[1]+cur[1])
            old=cur
            for k in range(1,21):
                t=k/20
                if c in ("C","S"):
                    u=1-t;p=(u**3*old[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*old[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1])
                else:
                    u=1-t;p=(u*u*old[0]+2*u*t*p1[0]+t*t*p3[0],u*u*old[1]+2*u*t*p1[1]+t*t*p3[1])
                add(p)
            prev_ctrl=p2 if c in ("C","S") else p1
        else: break
    return length,pts

def style(el):
    s=el.attrib.get("style","")
    st=dict(x.split(":",1) for x in s.split(";") if ":" in x)
    return (el.attrib.get("stroke",st.get("stroke","none")).strip().lower(),
            el.attrib.get("fill",st.get("fill","none")).strip().lower())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("svg");p.add_argument("--machine",choices=("60W","100W"),required=True)
    p.add_argument("--speed",choices=("100%","50%"),default="100%");p.add_argument("--scan",choices=("Normal","Left-to-right"),default="Normal")
    p.add_argument("--jct",choices=("ON","OFF"),default="ON");p.add_argument("--overhead-sec",type=float,default=120)
    p.add_argument("--vector-sec-per-m",type=float,default=None,help="Override experimental default")
    a=p.parse_args();root=ET.parse(a.svg).getroot()
    totals={"blue":0.,"green":0.,"red":0.,"black":0.};fills=0.;counts={k:0 for k in totals};fill_bbox_area=0.; warnings=[]
    for el in root.iter():
        tag=el.tag.split("}")[-1]
        stroke,fill=style(el)
        if tag=="path" and el.attrib.get("d"):
            length,pts=path_length(el.attrib["d"])
            cat=None
            if stroke in ("#0000ff","blue","rgb(0,0,255)"):cat="blue"
            elif stroke in ("#00ff00","green","rgb(0,255,0)"):cat="green"
            elif stroke in ("#ff0000","red","rgb(255,0,0)"):cat="red"
            elif stroke in ("#000000","black","rgb(0,0,0)"):cat="black"
            if cat: totals[cat]+=length;counts[cat]+=1
            if fill not in ("none","transparent") and pts:
                xs=[v[0] for v in pts];ys=[v[1] for v in pts]
                fill_bbox_area+=max(0,(max(xs)-min(xs))*(max(ys)-min(ys)))
                fills+=1
        if "transform" in el.attrib:warnings.append("SVG transform attribute found; this experimental parser does not apply transforms.")
    if root.attrib.get("viewBox"): warnings.append("viewBox present; parser assumes coordinate units map directly to mm. Check SVG physical size.")
    cut=totals["blue"];vector=totals["green"]+totals["red"]
    rate=cut_rate(a.machine,"JcT "+a.jct)
    cut_sec=cut*rate if rate else 0
    v_rate=a.vector_sec_per_m if a.vector_sec_per_m is not None else (25 if a.machine=="60W" else 29)
    vec_sec=vector/1000*v_rate
    fill_sec=0;fm=fill_model(a.machine,a.speed,a.scan)
    if fill_bbox_area and fm: fill_sec=max(0,fm[0]*fill_bbox_area+fm[1])
    total=cut_sec+vec_sec+fill_sec+a.overhead_sec
    print("\nLASERPREP — REAL SVG EXPERIMENTAL ESTIMATE")
    print("="*55);print(f"File: {Path(a.svg).name}");print(f"Machine: {a.machine} | JcT {a.jct}")
    print("Extracted rough path lengths (SVG units):")
    for k in totals:print(f"  {k:5s}: {totals[k]:,.1f} | {counts[k]} paths")
    print(f"Cutting length (blue): {cut:,.1f}");print(f"Cut estimate: {cut_sec:.1f}s")
    print(f"Vector engraving (green+red): {vector:,.1f}; rate {v_rate:.1f} s/m; estimate {vec_sec:.1f}s")
    print(f"Filled-path count: {fills}; SUM bounding-box area (rough, not true filled area): {fill_bbox_area:,.1f} SVG-unit²")
    print(f"Filled estimate (experimental): {fill_sec:.1f}s")
    print(f"Overhead: {a.overhead_sec:.1f}s")
    print("-"*55);print(f"ESTIMATED TOTAL: {total:.1f}s ({total/60:.2f} min)")
    print("Caution: SVG color mapping and unit scaling are provisional; black geometry is reported but excluded.")
    print("Fill uses bounding boxes (likely overestimate) and transforms are not applied.")
    print("This is a geometry extraction test tool; review results before trusting.")
    for w in set(warnings):print("WARNING:",w)
if __name__=="__main__":main()
