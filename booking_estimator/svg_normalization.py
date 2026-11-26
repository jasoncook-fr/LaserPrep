"""SVG path geometry mapped into physical millimetre viewport coordinates."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .geometry_pipeline import transform_segments
from .geometry import Matrix
from .primitive_extractor import extract_basic_shapes
from .viewport import viewbox_to_viewport_matrix
from .svg_units import parse_length_mm


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize_svg_paths(svg_source: str) -> list[dict[str, object]]:
    """Extract paths and normalize their coordinates into physical millimetres.

    Requires root physical width/height. When a viewBox exists, its viewport
    mapping honors preserveAspectRatio. Without a viewBox, coordinates are
    interpreted in the root SVG CSS-unit coordinate system and converted to mm.
    Root transforms are already included by the extractor.
    """
    root = ET.fromstring(svg_source)
    width, height = root.attrib.get("width"), root.attrib.get("height")
    if width is None or height is None:
        raise ValueError("SVG root must have physical width and height for mm normalization")
    viewbox = root.attrib.get("viewBox")
    if viewbox:
        viewport = viewbox_to_viewport_matrix(
            viewbox, width, height, root.attrib.get("preserveAspectRatio")
        )
    else:
        sx = parse_length_mm(width) / float(parse_length_mm(width))
        sy = parse_length_mm(height) / float(parse_length_mm(height))
        # No viewBox: CSS user coordinates are normally px; root dimensions
        # define the physical viewport but user coordinate scale is CSS px/mm.
        from .svg_units import _unit_scale_mm_per_user_unit
        viewport = Matrix(a=_unit_scale_mm_per_user_unit(width),
                         d=_unit_scale_mm_per_user_unit(height))

    records = []
    for record in extract_basic_shapes(svg_source):
        if record.element_type != "path":
            continue
        combined = viewport.compose(record.transform)
        records.append({
            "source_id": record.source_id,
            "source_element": record.source_element,
            "style": dict(record.style),
            "segments": transform_segments(combined, record.payload.get("segments", [])),
            "coordinate_unit": "mm",
        })
    return records
