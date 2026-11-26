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
        # SVG user coordinates default to CSS px when no viewBox is present.
        # Physical viewport dimensions do not change the px-to-mm user-unit scale.
        viewport = Matrix(a=25.4 / 96.0, d=25.4 / 96.0)

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
