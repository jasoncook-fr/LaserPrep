"""Convert extracted SVG primitive records into path-like segment records.

Rectangles, polylines, polygons, lines, circles, and ellipses are represented
using lines and SVG elliptical-arc segments. Rounded rectangles are supported.
"""
from __future__ import annotations

import math


def _line(a, b):
    return {"type": "line", "start": a, "end": b}


def _arc(a, rx, ry, end):
    return {"type": "arc", "start": a, "rx": rx, "ry": ry, "rotation": 0.0,
            "large_arc": 0, "sweep": 1, "end": end}


def primitive_to_segments(element_type: str, payload: dict) -> list[dict]:
    """Convert one extracted primitive payload to segment records."""
    t = element_type
    if t == "path":
        return list(payload.get("segments", []))
    if t == "line":
        return [_line((payload["x1"], payload["y1"]), (payload["x2"], payload["y2"]))]
    if t in {"polyline", "polygon"}:
        points = list(payload.get("points", []))
        segments = [_line(points[i], points[i+1]) for i in range(len(points)-1)]
        if t == "polygon" and len(points) > 1 and points[-1] != points[0]:
            segments.append(_line(points[-1], points[0]))
        return segments
    if t == "circle":
        cx, cy, r = payload["cx"], payload["cy"], payload["r"]
        if r == 0: return []
        p=[(cx+r,cy),(cx,cy+r),(cx-r,cy),(cx,cy-r),(cx+r,cy)]
        return [_arc(p[i],r,r,p[i+1]) for i in range(4)]
    if t == "ellipse":
        cx, cy, rx, ry = payload["cx"], payload["cy"], payload["rx"], payload["ry"]
        if rx == 0 or ry == 0: return []
        p=[(cx+rx,cy),(cx,cy+ry),(cx-rx,cy),(cx,cy-ry),(cx+rx,cy)]
        return [_arc(p[i],rx,ry,p[i+1]) for i in range(4)]
    if t == "rect":
        x,y,w,h=payload["x"],payload["y"],payload["width"],payload["height"]
        if w == 0 or h == 0: return []
        rx=min(abs(payload.get("rx",0)),w/2); ry=min(abs(payload.get("ry",0)),h/2)
        if rx == 0 or ry == 0:
            return [_line((x,y),(x+w,y)),_line((x+w,y),(x+w,y+h)),
                    _line((x+w,y+h),(x,y+h)),_line((x,y+h),(x,y))]
        segments=[_line((x+rx,y),(x+w-rx,y)),_arc((x+w-rx,y),rx,ry,(x+w,y+ry)),
          _line((x+w,y+ry),(x+w,y+h-ry)),_arc((x+w,y+h-ry),rx,ry,(x+w-rx,y+h)),
          _line((x+w-rx,y+h),(x+rx,y+h)),_arc((x+rx,y+h),rx,ry,(x,y+h-ry)),
          _line((x,y+h-ry),(x,y+ry)),_arc((x,y+ry),rx,ry,(x+rx,y))]
        return segments
    raise ValueError(f"Unsupported primitive type: {t!r}")
