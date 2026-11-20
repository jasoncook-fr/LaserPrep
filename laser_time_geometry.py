"""Experimental SVG geometry extraction for LaserPrep time-estimation research.

This module is intentionally standalone and does not alter LaserPrep's production
geometry pipeline. It flattens supported SVG geometry into transformed polylines
for length and approximate area analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
import xml.etree.ElementTree as ET
from typing import Optional

TOKEN_RE = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
TRANSFORM_RE = re.compile(r"([A-Za-z]+)\s*\(([^)]*)\)")
STYLE_KEYS = {"stroke", "fill", "stroke-width", "fill-rule", "opacity",
              "stroke-opacity", "fill-opacity", "display", "visibility"}

@dataclass
class Affine:
    # SVG matrix: x'=a*x+c*y+e, y'=b*x+d*y+f
    a: float=1.; b: float=0.; c: float=0.; d: float=1.; e: float=0.; f: float=0.
    def point(self, p):
        x,y=p
        return (self.a*x+self.c*y+self.e, self.b*x+self.d*y+self.f)
    def compose(self, other):
        """Return self * other: apply other, then self."""
        return Affine(self.a*other.a+self.c*other.b,
            self.b*other.a+self.d*other.b,
            self.a*other.c+self.c*other.d,
            self.b*other.c+self.d*other.d,
            self.a*other.e+self.c*other.f+self.e,
            self.b*other.e+self.d*other.f+self.f)
    @classmethod
    def parse(cls, text):
        result=cls()
        for name,args in TRANSFORM_RE.findall(text or ""):
            vals=[float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",args)]
            n=name.lower()
            t=cls()
            if n=="matrix" and len(vals)==6: t=cls(*vals)
            elif n=="translate" and len(vals) in (1,2): t=cls(e=vals[0],f=vals[1] if len(vals)>1 else 0.)
            elif n=="scale" and len(vals) in (1,2): t=cls(a=vals[0],d=vals[1] if len(vals)>1 else vals[0])
            elif n=="rotate" and len(vals) in (1,3):
                rad=math.radians(vals[0]); co,si=math.cos(rad),math.sin(rad)
                r=cls(co,si,-si,co)
                if len(vals)==3:
                    cx,cy=vals[1:]
                    t=cls(e=cx,f=cy).compose(r).compose(cls(e=-cx,f=-cy))
                else: t=r
            elif n=="skewx" and len(vals)==1: t=cls(c=math.tan(math.radians(vals[0])))
            elif n=="skewy" and len(vals)==1: t=cls(b=math.tan(math.radians(vals[0])))
            else: continue
            result=result.compose(t)
        return result

@dataclass
class GeometryPath:
    points: list[tuple[float,float]]
    closed: bool
    stroke: Optional[str]
    fill: Optional[str]
    fill_rule: str
    source_id: Optional[str]=None
    segment_count: int=0
    warnings: list[str]=field(default_factory=list)
    @property
    def length_mm(self):
        return sum(math.dist(a,b) for a,b in zip(self.points,self.points[1:]))
    @property
    def area_mm2(self):
        if not self.closed or len(self.points)<3: return 0.
        pts=self.points
        if pts[0]!=pts[-1]: pts=pts+[pts[0]]
        return abs(sum(x1*y2-x2*y1 for (x1,y1),(x2,y2) in zip(pts,pts[1:])))/2

@dataclass
class GeometryReport:
    paths: list[GeometryPath]=field(default_factory=list)
    warnings: list[str]=field(default_factory=list)
    unsupported_elements: list[str]=field(default_factory=list)
    unsupported_commands: dict[str,int]=field(default_factory=dict)
    @property
    def path_count(self): return len(self.paths)
    def category_lengths(self):
        out={"cut":0.,"vector":0.,"black_stroke":0.,"unclassified":0.}
        for p in self.paths:
            col=color_name(p.stroke)
            if col=="blue": out["cut"]+=p.length_mm
            elif col in ("red","green"): out["vector"]+=p.length_mm
            elif col=="black": out["black_stroke"]+=p.length_mm
            elif p.stroke: out["unclassified"]+=p.length_mm
        return out
    def fill_area(self):
        return sum(p.area_mm2 for p in self.paths if color_name(p.fill)=="black")

def color_name(value):
    if not value: return None
    v=value.strip().lower()
    if v in ("none","transparent"): return None
    named={"blue":"blue","green":"green","red":"red","black":"black"}
    if v in named:return named[v]
    if v.startswith("#"):
        h=v[1:]
        if len(h)==3:h="".join(ch*2 for ch in h)
        if len(h)==6:
            try: rgb=tuple(int(h[i:i+2],16) for i in (0,2,4))
            except ValueError:return None
            return { (0,0,255):"blue",(0,255,0):"green",(255,0,0):"red",(0,0,0):"black"}.get(rgb)
    m=re.fullmatch(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",v)
    if m:
        rgb=tuple(map(int,m.groups()))
        return {(0,0,255):"blue",(0,255,0):"green",(255,0,0):"red",(0,0,0):"black"}.get(rgb)
    return None

def _style(element, inherited):
    st=dict(inherited)
    for k,v in element.attrib.items():
        key=k.split("}")[-1]
        if key in STYLE_KEYS: st[key]=v.strip()
    for item in element.get("style","").split(";"):
        if ":" in item:
            k,v=item.split(":",1); k=k.strip()
            if k in STYLE_KEYS:st[k]=v.strip()
    return st

def _float_list(s):
    return [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",s or "")]

def _flatten_path(d, tolerance=0.5):
    """Return subpaths as point lists, closure flags, command count, unsupported set."""
    toks=TOKEN_RE.findall(d or ""); idx=0; cmd=None; pos=(0.,0.); start=(0.,0.)
    subs=[]; pts=[]; closed=False; count=0; unsupported=set()
    def flush():
        nonlocal pts,closed
        if pts: subs.append((pts,closed)); pts=[]; closed=False
    def add(p):
        nonlocal pos,count
        if not pts: pts.append(pos)
        pts.append(p); pos=p; count+=1
    def curve_sample(fn, steps):
        prev=pos
        for j in range(1,steps+1):
            p=fn(j/steps); pts.append(p)
        return p
    while idx<len(toks):
        if toks[idx].isalpha():cmd=toks[idx];idx+=1
        if cmd is None:break
        c=cmd.upper(); rel=cmd.islower()
        if c=="Z":
            if pts:
                if pts[-1]!=start:pts.append(start)
                closed=True;flush();pos=start;count+=1
            cmd=None;continue
        try:
            if c=="M":
                x,y=map(float,toks[idx:idx+2]);idx+=2
                p=(x+pos[0],y+pos[1]) if rel else (x,y)
                flush();pos=start=p;pts=[p];cmd="l" if rel else "L";count+=1
            elif c=="L":
                x,y=map(float,toks[idx:idx+2]);idx+=2;add((x+pos[0],y+pos[1]) if rel else (x,y))
            elif c=="H":
                x=float(toks[idx]);idx+=1;add((x+pos[0],pos[1]) if rel else (x,pos[1]))
            elif c=="V":
                y=float(toks[idx]);idx+=1;add((pos[0],y+pos[1]) if rel else (pos[0],y))
            elif c in ("C","S"):
                vals=list(map(float,toks[idx:idx+(6 if c=="C" else 4)]));idx+=len(vals)
                p0=pos
                if c=="C":
                    p1=(vals[0]+p0[0],vals[1]+p0[1]) if rel else vals[:2]
                    p2=(vals[2]+p0[0],vals[3]+p0[1]) if rel else vals[2:4]
                    p3=(vals[4]+p0[0],vals[5]+p0[1]) if rel else vals[4:6]
                else:
                    p1=p0; p2=(vals[0]+p0[0],vals[1]+p0[1]) if rel else vals[:2]
                    p3=(vals[2]+p0[0],vals[3]+p0[1]) if rel else vals[2:4]
                p1=tuple(p1);p2=tuple(p2);p3=tuple(p3)
                steps=max(8,int(math.dist(p0,p3)/max(tolerance,0.05)))
                curve_sample(lambda t:((1-t)**3*p0[0]+3*(1-t)**2*t*p1[0]+3*(1-t)*t*t*p2[0]+t**3*p3[0],
                    (1-t)**3*p0[1]+3*(1-t)**2*t*p1[1]+3*(1-t)*t*t*p2[1]+t**3*p3[1]),steps);pos=p3;count+=1
            elif c in ("Q","T"):
                vals=list(map(float,toks[idx:idx+(4 if c=="Q" else 2)]));idx+=len(vals);p0=pos
                if c=="Q":
                    p1=(vals[0]+p0[0],vals[1]+p0[1]) if rel else tuple(vals[:2])
                    p2=(vals[2]+p0[0],vals[3]+p0[1]) if rel else tuple(vals[2:4])
                else:p1=p0;p2=(vals[0]+p0[0],vals[1]+p0[1]) if rel else tuple(vals[:2])
                steps=max(8,int(math.dist(p0,p2)/max(tolerance,0.05)))
                curve_sample(lambda t:((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0],(1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]),steps);pos=p2;count+=1
            elif c=="A":
                # SVG elliptical arcs: approximate via endpoint-to-center conversion.
                vals=list(map(float,toks[idx:idx+7]));idx+=7
                rx,ry,rot,large,sweep,x,y=vals;end=(x+pos[0],y+pos[1]) if rel else (x,y)
                arc=_arc_points(pos,end,rx,ry,rot,int(large),int(sweep),tolerance)
                pts.extend(arc[1:]);pos=end;count+=1
            else:
                unsupported.add(c);break
        except (ValueError,IndexError):
            unsupported.add(c);break
    flush()
    return subs,count,unsupported

def _arc_points(p0,p1,rx,ry,rotation,large,sweep,tolerance):
    rx,ry=abs(rx),abs(ry)
    if not rx or not ry or p0==p1:return [p0,p1]
    phi=math.radians(rotation%360);co,si=math.cos(phi),math.sin(phi)
    dx=(p0[0]-p1[0])/2;dy=(p0[1]-p1[1])/2
    xp=co*dx+si*dy;yp=-si*dx+co*dy
    lam=xp*xp/(rx*rx)+yp*yp/(ry*ry)
    if lam>1:scale=math.sqrt(lam);rx*=scale;ry*=scale
    sign=-1 if large==sweep else 1
    num=max(0,rx*rx*ry*ry-rx*rx*yp*yp-ry*ry*xp*xp)
    den=rx*rx*yp*yp+ry*ry*xp*xp
    coef=sign*math.sqrt(num/den) if den else 0.
    cxp=coef*rx*yp/ry;cyp=-coef*ry*xp/rx
    cx=co*cxp-si*cyp+(p0[0]+p1[0])/2;cy=si*cxp+co*cyp+(p0[1]+p1[1])/2
    def angle(u,v):return math.atan2(u[0]*v[1]-u[1]*v[0],u[0]*v[0]+u[1]*v[1])
    u=((xp-cxp)/rx,(yp-cyp)/ry);v=((-xp-cxp)/rx,(-yp-cyp)/ry)
    theta=math.atan2(u[1],u[0]);delta=angle(u,v)
    if not sweep and delta>0:delta-=2*math.pi
    if sweep and delta<0:delta+=2*math.pi
    steps=max(8,int(abs(delta)*max(rx,ry)/max(tolerance,0.05)))
    result=[]
    for i in range(steps+1):
        t=theta+delta*i/steps;xx=rx*math.cos(t);yy=ry*math.sin(t)
        result.append((cx+co*xx-si*yy,cy+si*xx+co*yy))
    result[0]=p0;result[-1]=p1
    return result

def extract_svg(source, tolerance_mm=0.5):
    """Extract SVG path geometry from a filepath or SVG text."""
    report=GeometryReport()
    try:
        if hasattr(source,"read"): root=ET.parse(source).getroot()
        elif isinstance(source,str) and source.lstrip().startswith("<"):root=ET.fromstring(source)
        else:root=ET.parse(source).getroot()
    except Exception as exc:
        report.warnings.append(f"Unable to parse SVG: {exc}");return report
    def walk(el,style,transform):
        st=_style(el,style)
        if st.get("display","").lower()=="none" or st.get("visibility","").lower()=="hidden":return
        local=Affine.parse(el.get("transform",""));tx=transform.compose(local)
        tag=el.tag.split("}")[-1]
        if tag=="path":
            d=el.get("d","");subs,seg,unsupported=_flatten_path(d,tolerance_mm)
            if unsupported:
                for cmd in unsupported:report.unsupported_commands[cmd]=report.unsupported_commands.get(cmd,0)+1
                report.warnings.append(f"Path {el.get('id','(no id)')}: unsupported command(s) {','.join(sorted(unsupported))}; path may be incomplete.")
            for pts,closed in subs:
                transformed=[tx.point(p) for p in pts]
                report.paths.append(GeometryPath(transformed,closed,color_name(st.get("stroke")),color_name(st.get("fill")),st.get("fill-rule","nonzero"),el.get("id"),seg))
        elif tag in ("rect","line","polyline","polygon","circle","ellipse"):
            report.unsupported_elements.append(tag)
        elif tag not in ("svg","g","defs","clipPath","metadata","title","desc","style","symbol"):
            report.unsupported_elements.append(tag)
        for child in el:
            walk(child,st,tx)
    walk(root,{"fill":"black","stroke":"none"},Affine())
    if report.unsupported_elements:
        unique=sorted(set(report.unsupported_elements))
        report.warnings.append("Non-path geometry elements not converted: "+", ".join(unique))
    return report

def report_dict(report):
    lengths=report.category_lengths()
    return {"path_count":report.path_count,"lengths_mm":lengths,"black_fill_area_mm2":report.fill_area(),
            "unsupported_commands":dict(report.unsupported_commands),"unsupported_elements":sorted(set(report.unsupported_elements)),
            "warnings":report.warnings}
