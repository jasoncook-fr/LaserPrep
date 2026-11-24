#!/usr/bin/env python3
"""Inspect SVG dimensions, raw color distributions, path counts and current geometry lengths."""
import re, csv, sys, xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
from math import cos,sin,radians
from svgpathtools import parse_path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from provisional_estimator import estimate
DIR=Path("/home/jaz/Nextcloud/LaserPrep/TMP/TIME_TEST_FILES")
OUT=DIR/"geometry_diagnostics.csv"
PT=25.4/72
COL={"blue":"#0000ff","green":"#00ff00","red":"#ff0000","black":"#000000"}
def color(v):
 if not v:return None
 v=v.strip().lower()
 if v=="blue":return "#0000ff"
 if v=="green":return "#008000"
 if v=="lime":return "#00ff00"
 if v=="red":return "#ff0000"
 if v=="black":return "#000000"
 if v=="none" or v=="transparent":return None
 if v.startswith("#") and len(v)==4:v="#"+"".join(x*2 for x in v[1:])
 m=re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",v)
 if m:return "#"+"".join(f"{int(x):02x}" for x in m.groups())
 return v
def style(n):
 d={}
 for x in n.attrib.get("style","").split(";"):
  if ":" in x:k,v=x.split(":",1);d[k.strip()]=v.strip()
 d.update(n.attrib);return d
def mul(A,B):
 a,b,c,d,e,f=A;g,h,i,j,k,l=B
 return(a*g+c*h,b*g+d*h,a*i+c*j,b*i+d*j,a*k+c*l+e,b*k+d*l+f)
def trans(s):
 R=(1,0,0,1,0,0)
 for nm,args in re.findall(r"([a-zA-Z]+)\s*\(([^)]*)\)",s or ""):
  v=[float(x) for x in re.split(r"[,\s]+",args.strip()) if x]
  if nm=="matrix" and len(v)==6:M=tuple(v)
  elif nm=="translate":M=(1,0,0,1,v[0],v[1] if len(v)>1 else 0)
  elif nm=="scale":M=(v[0],0,0,v[1] if len(v)>1 else v[0],0,0)
  elif nm=="rotate":
   q=radians(v[0]);c,s=cos(q),sin(q);M=(c,s,-s,c,0,0)
   if len(v)>=3:M=mul((1,0,0,1,v[1],v[2]),mul(M,(1,0,0,1,-v[1],-v[2])))
  else:continue
  R=mul(R,M)
 return R
def length(p,M,scale):
 if M==(1,0,0,1,0,0):return p.length(error=1e-4)*scale
 a,b,c,d,e,f=M;total=0
 for seg in p:
  prev=None
  for i in range(101):
   z=seg.point(i/100);cur=complex(a*z.real+c*z.imag+e,b*z.real+d*z.imag+f)
   if prev is not None:total+=abs(cur-prev)
   prev=cur
 return total*scale
def parse(file):
 root=ET.parse(file).getroot();L=Counter();SC=Counter();FC=Counter();PC=Counter();err=0;paths=0
 def physical_mm(s):
  m=re.fullmatch(r"\s*([0-9.]+)\s*(mm|cm|in|inch|pt|px)?\s*",(s or "").lower())
  if not m:return None
  v=float(m.group(1));u=m.group(2) or "px"
  return v*{"mm":1,"cm":10,"in":25.4,"inch":25.4,"pt":25.4/72,"px":25.4/96}[u]
 vb=root.attrib.get("viewBox","").split(); scale=PT
 if len(vb)==4:
  dw=physical_mm(root.attrib.get("width")); dh=physical_mm(root.attrib.get("height"))
  if dw:scale=dw/float(vb[2])
  elif dh:scale=dh/float(vb[3])
 def walk(n,inh,M):
  nonlocal err,paths
  tag=n.tag.split("}",1)[-1]
  if tag in ("defs","clipPath","symbol"):return
  st=dict(inh);st.update(style(n));M2=mul(M,trans(n.attrib.get("transform","")))
  if tag=="path" and n.attrib.get("d"):
   paths+=1;stroke=color(st.get("stroke"));fill=color(st.get("fill","black"));SC[str(stroke)]+=1;FC[str(fill)]+=1
   if stroke in COL.values():PC[next(k for k,v in COL.items() if v==stroke)]+=1
   try:
    p=parse_path(n.attrib["d"])
    if stroke in (COL["blue"],COL["green"],COL["red"]):L[next(k for k,v in COL.items() if v==stroke)]+=length(p,M2,scale)
   except Exception as ex:err+=1;print("PATH ERROR",file.name,ex,file=sys.stderr)
  for ch in n:walk(ch,st,M2)
 walk(root,{},(1,0,0,1,0,0))
 return root.attrib,L,SC,FC,PC,err,paths,scale
def main():
 rows=[]
 for f in sorted(DIR.glob("*.svg")):
  m=re.match(r"^(\d+)m(\d+)s",f.name);machine=re.search(r"(60W|100W)",f.name,re.I)
  if not m or not machine:print("SKIP",f.name);continue
  actual=int(m[1])*60+int(m[2]);mach=machine[1].upper()
  a,L,SC,FC,PC,err,n,scale=parse(f);vb=a.get("viewBox","missing");w=a.get("width","missing");h=a.get("height","missing")
  print("\n"+f.name);print(f"  width={w} height={h} viewBox={vb} path elements={n}")
  print("  stroke counts:",dict(SC));print("  fill counts:",dict(FC));print("  target stroke path counts:",dict(PC))
  black_fill_count=FC.get("#000000",0)
  print(f"  measured length (physical viewBox scale): blue={L['blue']:.2f} green={L['green']:.2f} red={L['red']:.2f} mm; black-filled paths={black_fill_count}, scale={scale:.5f} mm/unit")
  est=estimate(machine=mach,blue_straight_mm=L['blue'],green_vector_mm=L['green'],red_vector_mm=L['red'],overhead_seconds=120)
  rows.append(dict(file=f.name,machine=mach,actual_seconds=actual,width=w,height=h,viewBox=vb,path_count=n,stroke_counts=str(dict(SC)),fill_counts=str(dict(FC)),blue_paths=PC.get('blue',0),green_paths=PC.get('green',0),red_paths=PC.get('red',0),blue_mm=L['blue'],green_mm=L['green'],red_mm=L['red'],black_fill_paths=FC.get('#000000',0),parse_errors=err,estimate_seconds=est['total_seconds'],error_seconds=est['total_seconds']-actual))
 with OUT.open("w",newline="",encoding="utf-8") as o:
  wr=csv.DictWriter(o,fieldnames=rows[0].keys());wr.writeheader();wr.writerows(rows)
 print("\nDiagnostic CSV:",OUT)
if __name__=="__main__":main()
