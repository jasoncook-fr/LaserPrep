"""Unified normalized SVG geometry extraction and measurement in millimetres."""
from __future__ import annotations
import xml.etree.ElementTree as ET

from .geometry import Matrix
from .geometry_pipeline import transform_segments
from .primitive_extractor import extract_basic_shapes
from .primitive_to_segments import primitive_to_segments
from .viewport import viewbox_to_viewport_matrix
from .lengths import path_length


def analyze_svg_geometry(svg_source: str, tolerance_mm: float = 1e-5) -> dict:
    """Normalize all supported SVG shapes and return element and aggregate lengths.

    Unsupported/failed elements are reported, never silently treated as measured.
    Coordinates and lengths are millimetres. Text/images and definitions are not
    measured; arbitrary path primitives outside the supported extractor scope are
    omitted with warnings where identifiable.
    """
    root=ET.fromstring(svg_source)
    width,height=root.attrib.get("width"),root.attrib.get("height")
    if width is None or height is None:
        raise ValueError("SVG root must have physical width and height for mm normalization")
    vb=root.attrib.get("viewBox")
    viewport=(viewbox_to_viewport_matrix(vb,width,height,root.attrib.get("preserveAspectRatio"))
              if vb else Matrix(a=25.4/96.0,d=25.4/96.0))
    results=[]; warnings=[]; total=0.0
    try:
        records=extract_basic_shapes(svg_source)
    except Exception as exc:
        raise ValueError(f"SVG extraction failed: {exc}") from exc
    for rec in records:
        try:
            segments=primitive_to_segments(rec.element_type,rec.payload)
            matrix=viewport.compose(rec.transform)
            normalized=transform_segments(matrix,segments)
            length=path_length(normalized,tolerance=tolerance_mm)
            results.append({"source_id":rec.source_id,"source_element":rec.source_element,
              "element_type":rec.element_type,"style":dict(rec.style),"segments":normalized,
              "coordinate_unit":"mm","length_mm":length})
            total+=length
        except Exception as exc:
            warnings.append({"source_id":rec.source_id,"element_type":rec.element_type,
                            "message":str(exc)})
    return {"elements":results,"total_length_mm":total,"coordinate_unit":"mm",
            "warnings":warnings,"measurement_tolerance_mm":tolerance_mm}
