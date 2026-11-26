"""Higher-level geometric workload profile from normalized measurement output."""
from __future__ import annotations

from collections import Counter
from .lengths import segment_length

CURVE_TYPES = {"quadratic", "cubic", "arc", "transformed_arc"}


def build_geometry_profile(measurement: dict, short_segment_threshold_mm: float = 1.0) -> dict:
    """Build descriptive workload features; this is not a runtime prediction."""
    if short_segment_threshold_mm < 0:
        raise ValueError("short_segment_threshold_mm must be non-negative")
    elements = measurement.get("elements", [])
    segment_lengths = []
    type_lengths = Counter()
    type_counts = Counter()
    short_count = 0
    for element in elements:
        for segment in element.get("segments", []):
            kind = segment.get("type", "other")
            try:
                length = segment_length(segment)
            except (ValueError, KeyError, TypeError):
                continue
            segment_lengths.append((kind, length))
            type_lengths[kind] += length
            type_counts[kind] += 1
            if length < short_segment_threshold_mm:
                short_count += 1

    line_length = type_lengths.get("line", 0.0)
    curve_length = sum(type_lengths.get(k, 0.0) for k in CURVE_TYPES)
    total_length = sum(length for _, length in segment_lengths)
    closed_count = sum(bool(e.get("is_closed")) for e in elements)
    open_count = sum(not bool(e.get("is_closed")) for e in elements)
    bbox_areas = [e["area_mm2"] for e in elements if "area_mm2" in e]
    bbox_widths = [e["width_mm"] for e in elements if "width_mm" in e]
    bbox_heights = [e["height_mm"] for e in elements if "height_mm" in e]
    return {
        "profile_version": 1,
        "coordinate_unit": "mm",
        "measurement_coverage_status": measurement.get("coverage_status", "unknown"),
        "coverage_complete": bool(measurement.get("coverage_complete", False)),
        "warning_count": measurement.get("warning_count", len(measurement.get("warnings", []))),
        "element_count": len(elements),
        "segment_count": len(segment_lengths),
        "segment_type_counts": dict(type_counts),
        "segment_type_lengths_mm": dict(type_lengths),
        "total_length_mm": total_length,
        "line_length_mm": line_length,
        "curve_length_mm": curve_length,
        "closed_element_count": closed_count,
        "open_element_count": open_count,
        "short_segment_threshold_mm": short_segment_threshold_mm,
        "short_segment_count": short_count,
        "short_segment_fraction": short_count / len(segment_lengths) if segment_lengths else 0.0,
        "mean_segment_length_mm": total_length / len(segment_lengths) if segment_lengths else 0.0,
        "mean_element_length_mm": sum(e.get("length_mm", 0.0) for e in elements) / len(elements) if elements else 0.0,
        "element_length_total_mm": sum(e.get("length_mm", 0.0) for e in elements),
        "element_bbox_area_mean_mm2": sum(bbox_areas) / len(bbox_areas) if bbox_areas else 0.0,
        "element_bbox_width_mean_mm": sum(bbox_widths) / len(bbox_widths) if bbox_widths else 0.0,
        "element_bbox_height_mean_mm": sum(bbox_heights) / len(bbox_heights) if bbox_heights else 0.0,
        "document_bbox_width_mm": measurement.get("width_mm", 0.0),
        "document_bbox_height_mm": measurement.get("height_mm", 0.0),
        "document_bbox_area_mm2": measurement.get("area_mm2", 0.0),
    }
