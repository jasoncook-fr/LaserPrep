"""
svg_transform.py

LaserPrep
SVG Transform Utilities

Version 2.0

Adds matrix composition while remaining backward compatible.
"""

from __future__ import annotations
import copy
import re
from drawing import Point, Line, Bezier

MATRIX_RE = re.compile(r"matrix\s*\(\s*([^)]+)\s*\)")

class AffineTransform:
    def __init__(self,a=1,b=0,c=0,d=1,e=0,f=0):
        self.a=float(a); self.b=float(b); self.c=float(c)
        self.d=float(d); self.e=float(e); self.f=float(f)

    @classmethod
    def identity(cls):
        return cls()

    @classmethod
    def translation(cls,x,y):
        return cls(1,0,0,1,x,y)

    @classmethod
    def from_svg(cls,text):
        if not text:
            return cls.identity()
        m=MATRIX_RE.match(text.strip())
        if not m:
            raise ValueError(f"Unsupported transform: {text}")
        vals=[float(v.strip()) for v in m.group(1).split(",")]
        return cls(*vals)

    def combine(self, other):
        return AffineTransform(
            self.a*other.a + self.c*other.b,
            self.b*other.a + self.d*other.b,
            self.a*other.c + self.c*other.d,
            self.b*other.c + self.d*other.d,
            self.a*other.e + self.c*other.f + self.e,
            self.b*other.e + self.d*other.f + self.f,
        )

    def __matmul__(self, other):
        return self.combine(other)

    def apply_point(self,p):
        return Point(
            self.a*p.x + self.c*p.y + self.e,
            self.b*p.x + self.d*p.y + self.f
        )

    def apply_line(self,line):
        obj=copy.deepcopy(line)
        obj.start=self.apply_point(obj.start)
        obj.end=self.apply_point(obj.end)
        return obj

    def apply_bezier(self,b):
        obj=copy.deepcopy(b)
        obj.start=self.apply_point(obj.start)
        obj.control1=self.apply_point(obj.control1)
        obj.control2=self.apply_point(obj.control2)
        obj.end=self.apply_point(obj.end)
        return obj

    def apply(self,obj):
        if isinstance(obj,Line): return self.apply_line(obj)
        if isinstance(obj,Bezier): return self.apply_bezier(obj)
        if isinstance(obj,Point): return self.apply_point(obj)
        raise TypeError(type(obj))
