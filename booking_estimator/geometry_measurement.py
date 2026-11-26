"""Unified normalized SVG geometry extraction and measurement in millimetres."""
from __future__ import annotations
import xml.etree.ElementTree as ET

from .geometry import Matrix
from .geometry_pipeline import transform_segments
from .primitive_extractor import extract_basic_shapes
from .primitive_to_segments import primitive_to_segments
from .viewport import viewbox_to_viewport_matrix
from .lengths import path_length

SUPPORTED = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path"}
CONTAINER = {"svg", "g", "defs", "symbol", "clipPath", "mask", "metadata", "title", "desc"}
NON_DRAWING = {"style", "script", "linearGradient", "radialGradient", "stop", "pattern", "marker", "filter", "feGaussianBlur", "feColorMatrix", "feBlend", "feOffset", "feFlood", "feComposite", "feMerge", "feMergeNode", "animate", "animateTransform", "animateMotion", "set"}


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
            results.append({"source_id":rec.source_id,"source_element":rec.source_element,
              "element_type":rec.element_type,"style":dict(rec.style),"segments":normalized,
              "coordinate_unit":"mm","length_mm":length,"segment_count":len(normalized),\n              "segment_type_counts":counts})
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
    return {"elements":results,"total_length_mm":total,"coordinate_unit":"mm",
            "warnings":warnings,"measurement_tolerance_mm":tolerance_mm,
            "coverage_complete":len(warnings)==0,
            "coverage_status":"complete" if not warnings else "partial",
            "warning_count":len(warnings),"warning_element_types":warning_types,
            "measured_element_count":len(results),\n            "total_segment_count":sum(segment_counts.values()),\n            "segment_type_counts":segment_counts}
