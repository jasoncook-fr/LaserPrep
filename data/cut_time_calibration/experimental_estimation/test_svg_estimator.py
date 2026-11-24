#!/usr/bin/env python3
"""Isolated experimental SVG cut-time estimator. Research use only; not production."""
import argparse, csv, math, re, xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/"data/cut_time_calibration/controlled_tests_master.csv"
TOKEN=re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
COLORS={"blue":"blue","green":"green","red":"red","black":"black"}
RGB={"blue":(0,0,255),"green":(0,255,0),"red":(255,0,0),"black":(0,0,0)}
def color(v):
    if not v:return None
    v=v.strip().lower()
    if v in COLORS:return v
    if v=="none":return None
    if v.startswith("#") and len(v)==4:v="#"+"".join(x*2 for x in v[1:])
    if v.startswith("#") and len(v)==7:
        try:return next((k for k,c in RGB.items() if tuple(int(v[i:i+2],16) for i in (1,3,5))==c),None)
        except ValueError:return None
    m=re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",v)
    if m:return next((k for k,c in RGB.items() if tuple(map(int,m.groups()))==c),None)
    return None
def cubic(a,b,c,d,t):
    u=1-t
    return (u**3*a[0]+3*u*u*t*b[0]+3*u*t*t*c[0]+t**3*d[0],u**3*a[1]+3*u*u*t*b[1]+3*u*t*t*c[1]+t**3*d[1])
def path_parse(d):
    tok=TOKEN.findall(d or ""); i=0; cmd=None; pos=(0.,0.); start=None; sub=[]; cur=[]; length=0.; unsupported=[]
    def add(p):
        nonlocal pos,length,cur
        if cur:length+=math.dist(pos,p)
        cur.append(p);pos=p
    while i<len(tok):
        if tok[i].isalpha():cmd=tok[i];i+=1
        if not cmd:break
        c=cmd.upper();rel=cmd.islower()
        if c not in "MLHVCZ":unsupported.append(c);break
        if c=="Z":
            if cur and start:
                length+=math.dist(pos,start);cur.append(start);sub.append(cur);cur=[];pos=start
            cmd=None;continue
        try:
            if c=="M":
                x,y=float(tok[i]),float(tok[i+1]);i+=2;p=(x+pos[0],y+pos[1]) if rel else (x,y)
                if cur:sub.append(cur)
                pos=p;start=p;cur=[p];cmd="l" if rel else "L"
            elif c=="L":
                x,y=float(tok[i]),float(tok[i+1]);i+=2;add((x+pos[0],y+pos[1]) if rel else (x,y))
            elif c=="H":
                x=float(tok[i]);i+=1;add((x+pos[0],pos[1]) if rel else (x,pos[1]))
            elif c=="V":
                y=float(tok[i]);i+=1;add((pos[0],y+pos[1]) if rel else (pos[0],y))
            elif c=="C":
                v=list(map(float,tok[i:i+6]));i+=6;p0=pos
                p1=(v[0]+p0[0],v[1]+p0[1]) if rel else (v[0],v[1]);p2=(v[2]+p0[0],v[3]+p0[1]) if rel else (v[2],v[3]);p3=(v[4]+p0[0],v[5]+p0[1]) if rel else (v[4],v[5])
                prev=p0
                for k in range(1,31):
                    p=cubic(p0,p1,p2,p3,k/30);length+=math.dist(prev,p);cur.append(p);prev=p
                pos=p3
        except (IndexError,ValueError):unsupported.append("malformed "+c);break
    if cur:sub.append(cur)
    return sub,length,unsupported
def area(poly):
    if len(poly)<3:return 0
    pts=poly if poly[0]==poly[-1] else poly+[poly[0]]
    return abs(sum(pts[i][0]*pts[i+1][1]-pts[i+1][0]*pts[i][1] for i in range(len(pts)-1))/2)
def fit_fill(machine,speed,scan):
    group=f"Filled test {speed} speed";xs=[];ys=[];ids=[]
    with DATA.open(newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("measurement_type")!="filled engraving" or r.get("machine")!=machine or r.get("test_group")!=group or r.get("optimization")!=scan:continue
            m=re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm",r.get("geometry",""),re.I)
            if m:xs.append(float(m.group(1))*float(m.group(2)));ys.append(float(r["actual_time_seconds"]));ids.append(r["record_id"])
    if len(xs)<2:raise ValueError("Missing calibration rows for selected fill condition.")
    xm=sum(xs)/len(xs);ym=sum(ys)/len(ys);ss=sum((x-xm)**2 for x in xs)
    slope=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/ss;inter=ym-slope*xm
    sst=sum((y-ym)**2 for y in ys);sse=sum((y-(slope*x+inter))**2 for x,y in zip(xs,ys))
    return slope,inter,1-sse/sst if sst else float("nan"),ids
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("svg",type=Path);ap.add_argument("--machine",choices=["60W","100W"],required=True)
    ap.add_argument("--fill-speed",choices=["50%","100%"],default="100%")
    ap.add_argument("--scan",choices=["Normal","Left-to-right"],default="Normal")
    ap.add_argument("--optimization",choices=["ON","OFF","UNKNOWN"],default="UNKNOWN")
    ap.add_argument("--save-report",type=Path)
    args=ap.parse_args();blue=green=red=blackstroke=fillarea=0.;count=0;warn=[]
    try:root=ET.parse(args.svg).getroot()
    except Exception as e:ap.error(f"Could not parse SVG: {e}")
    if any(el.get("transform") for el in root.iter()):warn.append("SVG transform attributes detected; geometry is NOT transformed in this estimate.")
    for el in root.iter():
        if el.tag.split("}")[-1]!="path":continue
        d=el.get("d","");style={}
        for kv in el.get("style","").split(";"):
            if ":" in kv:k,v=kv.split(":",1);style[k.strip()]=v.strip()
        sc=color(el.get("stroke",style.get("stroke")));fc=color(el.get("fill",style.get("fill")))
        sub,l,unsupported=path_parse(d);count+=1
        if unsupported:warn.append("Unsupported path command(s): "+", ".join(unsupported))
        if sc=="blue":blue+=l
        elif sc=="green":green+=l
        elif sc=="red":red+=l
        elif sc=="black":blackstroke+=l
        if fc=="black":fillarea+=sum(area(p) for p in sub)
    # legacy best-effort vector rates; deliberately flagged as low confidence
    cut_rates={"60W":21.2,"100W":21.1};vector_rates={"60W":36.0,"100W":31.4}
    cut_s=blue/1000*cut_rates[args.machine];vector_s=(green+red+blackstroke)/1000*vector_rates[args.machine]
    slope,inter,r2,ids=fit_fill(args.machine,args.fill_speed,args.scan)
    fill_s=slope*fillarea+inter if fillarea else 0
    total=cut_s+vector_s+fill_s
    lines=["EXPERIMENTAL LASER TIME ESTIMATE","="*36,f"File: {args.svg.name}",f"Machine: {args.machine} | Vector optimization: {args.optimization}",f"Fill calibration: {args.fill_speed} speed / {args.scan}",f"Paths scanned: {count}",f"Blue cut length: {blue:,.1f} mm -> {cut_s:.1f} s (provisional legacy rate)",f"Green+red+black stroke length: {green+red+blackstroke:,.1f} mm -> {vector_s:.1f} s (provisional pooled legacy rate)",f"Black filled area: {fillarea:,.1f} mm² -> {fill_s:.1f} s (fit: {slope*1000:.3f} s/1000mm² + {inter:.2f}s)",f"Fill fit R²={r2:.4f}; records={','.join(ids)}","-"*36,f"PROVISIONAL TOTAL: {total:.1f} s ({total/60:.2f} min)","Confidence: fill component is condition-specific regression from 3 calibration points; cut/vector components are exploratory legacy rates and not validated."]
    lines+=["WARNINGS:"]+["- "+w for w in sorted(set(warn))]+["- Filled area uses approximate polygon area; subpath/hole semantics, non-black fills, SVG transforms, units, and unsupported path commands may cause errors.","- The fill regression is applied only to detected black-filled path geometry; SVG fill area extraction may not match laser scan-path length.","- The model does not apply OPT/JcT/material/profile multipliers; these are not validated.","- Experimental only; not connected to production processing, acceptance, or rejection."]
    out="\n".join(lines);print(out)
    if args.save_report:args.save_report.write_text(out+"\n",encoding="utf-8")
if __name__=="__main__":main()
