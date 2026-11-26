"""Geometric direction-change and local complexity indicators (Stage 11)."""
from __future__ import annotations
import math
from .geometry import Point
from .geometry_measurement import _arc_points


def _unit(vector):
    x, y = vector
    norm = math.hypot(x, y)
    return None if norm == 0 else (x / norm, y / norm)


def _tangents(segment):
    kind = segment.get("type")
    if kind == "transformed_arc":
        original, matrix = segment["segment"], segment["matrix"]
        pts = _arc_points(original, samples=128)
        p0, p1 = matrix.apply(Point(*pts[0])), matrix.apply(Point(*pts[1]))
        pn, pe = matrix.apply(Point(*pts[-2])), matrix.apply(Point(*pts[-1]))
        return _unit((p1.x-p0.x,p1.y-p0.y)), _unit((pe.x-pn.x,pe.y-pn.y))
    if kind == "arc":
        pts = _arc_points(segment, samples=128)
        return _unit((pts[1][0]-pts[0][0],pts[1][1]-pts[0][1])), _unit((pts[-1][0]-pts[-2][0],pts[-1][1]-pts[-2][1]))
    if kind == "line":
        v=(segment["end"][0]-segment["start"][0],segment["end"][1]-segment["start"][1])
        u=_unit(v)
        return u,u
    if kind == "quadratic":
        p0,p1,p2=segment["start"],segment["control"],segment["end"]
        return _unit((p1[0]-p0[0],p1[1]-p0[1])),_unit((p2[0]-p1[0],p2[1]-p1[1]))
    if kind == "cubic":
        p0,p1,p2,p3=segment["start"],segment["control1"],segment["control2"],segment["end"]
        return _unit((p1[0]-p0[0],p1[1]-p0[1])),_unit((p3[0]-p2[0],p3[1]-p2[1]))
    return None,None


def _turn_angle(incoming, outgoing):
    if incoming is None or outgoing is None:
        return None
    dot=max(-1.0,min(1.0,incoming[0]*outgoing[0]+incoming[1]*outgoing[1]))
    return math.degrees(math.acos(dot))


def analyze_geometry_complexity(measurement: dict, angle_thresholds_deg=(30.0,60.0,90.0), tolerance_mm=1e-5):
    """Analyze consecutive connected segment transitions; descriptive only."""
    if tolerance_mm <= 0:
        raise ValueError("tolerance_mm must be positive")
    thresholds=tuple(float(t) for t in angle_thresholds_deg)
    if any(t < 0 or t > 180 for t in thresholds):
        raise ValueError("Angle thresholds must be between 0 and 180 degrees")
    transitions=[]
    elements=measurement.get("elements",[])
    total_length=0.0
    for element in elements:
        segments=element.get("segments",[])
        total_length+=float(element.get("length_mm",0.0))
        for i in range(len(segments)-1):
            a,b=segments[i],segments[i+1]
            if a.get("type")=="transformed_arc":
                sa=a["segment"]["end"]; mat=a["matrix"]; p=mat.apply(Point(*sa)); end=(p.x,p.y)
            else: end=tuple(a.get("end",()))
            if b.get("type")=="transformed_arc":
                sb=b["segment"]["start"]; mat=b["matrix"]; p=mat.apply(Point(*sb)); start=(p.x,p.y)
            else: start=tuple(b.get("start",()))
            if len(end)!=2 or len(start)!=2 or math.hypot(end[0]-start[0],end[1]-start[1])>tolerance_mm:
                continue
            _,ta=_tangents(a); tb,_=_tangents(b)
            angle=_turn_angle(ta,tb)
            if angle is not None:
                transitions.append(angle)
    count=len(transitions)
    mean=sum(transitions)/count if count else 0.0
    sorted_angles=sorted(transitions)
    median=(sorted_angles[count//2] if count%2 else (sorted_angles[count//2-1]+sorted_angles[count//2])/2) if count else 0.0
    return {
        "complexity_version":1,
        "transition_count":count,
        "turn_angles_deg":transitions,
        "mean_turn_angle_deg":mean,
        "median_turn_angle_deg":median,
        "maximum_turn_angle_deg":max(transitions,default=0.0),
        "total_turn_angle_deg":sum(transitions),
        "turn_density_per_m":sum(transitions)/(total_length/1000.0) if total_length>0 else 0.0,
        "sharp_turn_counts":{str(t):sum(a>=t for a in transitions) for t in thresholds},
        "angle_thresholds_deg":thresholds,
        "connected_transitions_only":True,
        "measurement_coverage_status":measurement.get("coverage_status","unknown"),
        "coverage_complete":bool(measurement.get("coverage_complete",False)),
        "warning_count":measurement.get("warning_count",len(measurement.get("warnings",[]))),
        "total_length_mm":total_length,
    }
