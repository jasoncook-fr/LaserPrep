"""Integration helper for extracting SVG path geometry with hierarchy transforms applied.

Primitive extraction retains each record's composed element/group transform. This
module turns path records into explicitly transformed segment records, without
normalizing the SVG viewport or converting units.
"""
from __future__ import annotations

from .geometry_pipeline import transform_segments
from .primitive_extractor import extract_basic_shapes


def extract_transformed_paths(svg_source: str) -> list[dict[str, object]]:
    """Return path records whose parsed segments have their SVG transforms applied.

    Non-path geometry is intentionally omitted at this stage. Metadata and style
    are retained, and arcs remain explicit transformed_arc wrappers.
    """
    output: list[dict[str, object]] = []
    for record in extract_basic_shapes(svg_source):
        if record.element_type != "path":
            continue
        segments = record.payload.get("segments", [])
        output.append({
            "source_id": record.source_id,
            "source_element": record.source_element,
            "style": dict(record.style),
            "segments": transform_segments(record.transform, segments),
        })
    return output
