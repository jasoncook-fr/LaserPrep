"""Unified normalized SVG geometry extraction and measurement in millimetres."""
from __future__ import annotations
import math
import xml.etree.ElementTree as ET

from .geometry import Point

from .geometry import Matrix
from .geometry_pipeline import transform_segments
from .primitive_extractor import extract_basic_shapes
from .primitive_to_segments import primitive_to_segments
from .viewport import viewbox_to_viewport_matrix
from .lengths import path_length, _arc_parameters

SUPPORTED = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path"}
CONTAINER = {"svg", "g", "defs", "symbol", "clipPath", "mask", "metadata", "title", "desc"}
NON_DRAWING = {"style", "script", "linearGradient", "radialGradient", "stop", "pattern", "marker", "filter", "feGaussianBlur", "feColorMatrix", "feBlend", "feOffset", "feFlood", "feComposite", "feMerge", "feMergeNode", "animate", "animateTransform", "animateMotion", "set"}




def _segment_endpoints(segment):
    """Return normalized-mm start/end points, including transformed arcs."""
    kind=segment.get("type")
    if kind == "transformed_arc":
        original=segment["segment"]; matrix=segment["matrix"]
        start=matrix.apply(Point(*original["start"]))
        end=matrix.apply(Point(*original["end"]))
        return (start.x,start.y),(end.x,end.y)
    if kind in {"line","arc","quadratic","cubic"}:
        return tuple(segment["start"]),tuple(segment["end"])
    return None


def _topology(segments, tolerance):
    """Estimate segment-chain connectivity and closure in normalized mm."""
    endpoints=[_segment_endpoints(s) for s in segments]
    endpoints=[p for p in endpoints if p is not None]
    if not endpoints:
        return {"is_continuous":True,"is_closed":False,"subpath_count":0,
                "gap_count":0,"start_point_mm":None,"end_point_mm":None}
    gaps=sum(math.hypot(endpoints[i][1][0]-endpoints[i+1][0][0],
                        endpoints[i][1][1]-endpoints[i+1][0][1]) > tolerance
              for i in range(len(endpoints)-1))
    first,last=endpoints[0][0],endpoints[-1][1]
    closure_gap=math.hypot(first[0]-last[0],first[1]-last[1])
    continuous=gaps==0
    closed=continuous and closure_gap<=tolerance
    return {"is_continuous":continuous,"is_closed":closed,
            "subpath_count":gaps+1,"gap_count":gaps,
            "start_point_mm":first,"end_point_mm":last}

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _style(node: ET.Element, inherited: dict[str, str]) -> dict[str, str]:
    style = dict(inherited)
    for key in ("display", "visibility"):
        if key in node.attrib:
            style[key] = node.attrib[key]
    for part in node.attrib.get("style", "").split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            key = key.strip()
            if key in ("display", "visibility"):
                style[key] = value.strip()
    return style


def analyze_svg_geometry(svg_source: str, tolerance_mm: float = 1e-5) -> dict:
    """Normalize supported SVG shapes and report measurement and coverage warnings.

    Hidden geometry is excluded. Unsupported drawable elements and drawable
    elements inside definitions are reported as coverage warnings. Lengths are
    geometric centerline/perimeter lengths, not laser-operation predictions.
    """
    if tolerance_mm <= 0:
        raise ValueError("tolerance_mm must be positive")
    root=ET.fromstring(svg_source)
    width,height=root.attrib.get("width"),root.attrib.get("height")
    if width is None or height is None:
        raise ValueError("SVG root must have physical width and height for mm normalization")
    vb=root.attrib.get("viewBox")
    viewport=(viewbox_to_viewport_matrix(vb,width,height,root.attrib.get("preserveAspectRatio"))
              if vb else Matrix(a=25.4/96.0,d=25.4/96.0))
    results=[]; warnings=[]; total=0.0
    segment_counts={"line":0,"quadratic":0,"cubic":0,"arc":0,"transformed_arc":0,"other":0}
    # Collect explicit unsupported drawable nodes and track definition subtrees.
    def scan(node, inherited, in_defs=False):
        if not isinstance(node.tag, str):
            return
        tag=_local(node.tag); st=_style(node,inherited)
        hidden=(st.get("display", "").strip().lower()=="none" or
                st.get("visibility", "").strip().lower() in {"hidden", "collapse"})
        in_defs = in_defs or tag in {"defs", "symbol", "clipPath", "mask"}
        if hidden:
            return
        if tag not in SUPPORTED and tag not in CONTAINER and tag not in NON_DRAWING and tag not in {"text", "image", "use", "foreignObject"}:
            warnings.append({"source_id":node.attrib.get("id"),"element_type":tag,
                            "message":"Unsupported drawable or SVG element; not measured"})
        elif tag in {"text", "image", "use", "foreignObject"}:
            warnings.append({"source_id":node.attrib.get("id"),"element_type":tag,
                            "message":"Element is not measured by this analyzer"})
        if in_defs and tag in SUPPORTED:
            warnings.append({"source_id":node.attrib.get("id"),"element_type":tag,
                            "message":"Geometry inside definitions is not instantiated or measured"})
        for child in node:
            scan(child,st,in_defs)
    scan(root,{})
    try:
        records=extract_basic_shapes(svg_source)
    except Exception as exc:
        raise ValueError(f"SVG extraction failed: {exc}") from exc
    for rec in records:
        try:
            if rec.style.get("display", "").strip().lower()=="none" or rec.style.get("visibility", "").strip().lower() in {"hidden", "collapse"}:
                continue
            segments=primitive_to_segments(rec.element_type,rec.payload)
            matrix=viewport.compose(rec.transform)
            normalized=transform_segments(matrix,segments)
            length=path_length(normalized,tolerance=tolerance_mm)
            counts={key:0 for key in segment_counts}
            for segment in normalized:
                kind=segment.get("type","other")
                if kind not in counts: kind="other"
                counts[kind]+=1
                segment_counts[kind]+=1
            topology=_topology(normalized,tolerance_mm)
            bounds=_bounds(normalized)
            results.append({"source_id":rec.source_id,"source_element":rec.source_element,
              "element_type":rec.element_type,"style":dict(rec.style),"segments":normalized,
              "coordinate_unit":"mm","length_mm":length,"segment_count":len(normalized),
              "segment_type_counts":counts,**topology,**(bounds or {})})
            total+=length
        except Exception as exc:
            warnings.append({"source_id":rec.source_id,"element_type":rec.element_type,
                            "message":str(exc)})
    unique_warnings=[]; seen_warnings=set()
    for warning in warnings:
        signature=(warning.get("source_id"),warning.get("element_type"),warning.get("message"))
        if signature not in seen_warnings:
            seen_warnings.add(signature); unique_warnings.append(warning)
    warnings=unique_warnings
    warning_types=sorted({w.get("element_type", "unknown") for w in warnings})
    bounded=[e for e in results if "min_x_mm" in e]
    document_bounds=None
    if bounded:
        min_x=min(e["min_x_mm"] for e in bounded);min_y=min(e["min_y_mm"] for e in bounded)
        max_x=max(e["max_x_mm"] for e in bounded);max_y=max(e["max_y_mm"] for e in bounded)
        document_bounds={"min_x_mm":min_x,"min_y_mm":min_y,"max_x_mm":max_x,"max_y_mm":max_y,"width_mm":max_x-min_x,"height_mm":max_y-min_y,"area_mm2":(max_x-min_x)*(max_y-min_y)}
    return {"elements":results,**(document_bounds or {}),"total_length_mm":total,"coordinate_unit":"mm",
            "warnings":warnings,"measurement_tolerance_mm":tolerance_mm,
            "coverage_complete":len(warnings)==0,
            "coverage_status":"complete" if not warnings else "partial",
            "warning_count":len(warnings),"warning_element_types":warning_types,
            "measured_element_count":len(results),
            "total_segment_count":sum(segment_counts.values()),
            "segment_type_counts":segment_counts}
