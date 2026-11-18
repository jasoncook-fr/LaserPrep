"""
cut_time_estimator.py

Geometry measurements used by LaserPrep's laser-time estimator.

This first stage deliberately measures operation-specific geometry only.
It does not produce a duration until machine calibration values have been
validated and configured.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

from drawing import Bezier, Line, Path


BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

POINT_TOLERANCE_MM = 0.01
MAX_BEZIER_DEPTH = 16
JOIN_TOLERANCE_MM = 1e-7


@dataclass
class CutTimeGeometry:
    """Operation-specific geometry totals, expressed in millimetres."""

    cut_straight_length_mm: float = 0.0
    cut_curve_length_mm: float = 0.0
    green_engrave_straight_length_mm: float = 0.0
    green_engrave_curve_length_mm: float = 0.0
    red_engrave_straight_length_mm: float = 0.0
    red_engrave_curve_length_mm: float = 0.0
    black_fill_area_mm2: float = 0.0

    blue_paths: int = 0
    green_paths: int = 0
    red_paths: int = 0
    black_fill_paths: int = 0

    blue_segments: int = 0
    green_segments: int = 0
    red_segments: int = 0
    black_fill_segments: int = 0

    black_fill_unmeasurable_paths: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _distance(a, b) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def _split_bezier(segment: Bezier):
    """Split a cubic Bezier at t=0.5 using de Casteljau's algorithm."""
    p0, p1, p2, p3 = (
        segment.start,
        segment.control1,
        segment.control2,
        segment.end,
    )

    def midpoint(a, b):
        from drawing import Point
        return Point((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)

    p01 = midpoint(p0, p1)
    p12 = midpoint(p1, p2)
    p23 = midpoint(p2, p3)
    p012 = midpoint(p01, p12)
    p123 = midpoint(p12, p23)
    p0123 = midpoint(p012, p123)

    return (
        Bezier(p0, p01, p012, p0123, segment.stroke_color, segment.stroke_width),
        Bezier(p0123, p123, p23, p3, segment.stroke_color, segment.stroke_width),
    )


def bezier_length(segment: Bezier, tolerance: float = POINT_TOLERANCE_MM) -> float:
    """
    Approximate cubic Bezier length by adaptive subdivision.

    The difference between control-polygon length and endpoint chord
    bounds the local approximation error. This is more reliable than
    treating the control polygon itself as the actual curve length.
    """
    chord = _distance(segment.start, segment.end)
    polygon = (
        _distance(segment.start, segment.control1)
        + _distance(segment.control1, segment.control2)
        + _distance(segment.control2, segment.end)
    )

    if polygon - chord <= tolerance or MAX_BEZIER_DEPTH <= 0:
        return (polygon + chord) / 2.0

    left, right = _split_bezier(segment)
    return (
        _bezier_length_recursive(left, tolerance / 2.0, 1)
        + _bezier_length_recursive(right, tolerance / 2.0, 1)
    )


def _bezier_length_recursive(segment, tolerance, depth):
    chord = _distance(segment.start, segment.end)
    polygon = (
        _distance(segment.start, segment.control1)
        + _distance(segment.control1, segment.control2)
        + _distance(segment.control2, segment.end)
    )
    if polygon - chord <= tolerance or depth >= MAX_BEZIER_DEPTH:
        return (polygon + chord) / 2.0
    left, right = _split_bezier(segment)
    return (
        _bezier_length_recursive(left, tolerance / 2.0, depth + 1)
        + _bezier_length_recursive(right, tolerance / 2.0, depth + 1)
    )


def segment_length(segment) -> float:
    if isinstance(segment, Line):
        return _distance(segment.start, segment.end)
    if isinstance(segment, Bezier):
        return bezier_length(segment)
    return 0.0


def _same_point(a, b) -> bool:
    return (
        abs(a.x - b.x) <= JOIN_TOLERANCE_MM
        and abs(a.y - b.y) <= JOIN_TOLERANCE_MM
    )


def _split_subpaths(segments):
    rings = []
    current = []
    previous_end = None

    for segment in segments:
        if previous_end is not None and not _same_point(segment.start, previous_end):
            if current:
                rings.append(current)
            current = []
        current.append(segment)
        previous_end = segment.end

    if current:
        rings.append(current)
    return rings


def _flatten_bezier(segment, tolerance=POINT_TOLERANCE_MM, depth=0):
    chord = _distance(segment.start, segment.end)
    polygon = (
        _distance(segment.start, segment.control1)
        + _distance(segment.control1, segment.control2)
        + _distance(segment.control2, segment.end)
    )
    if polygon - chord <= tolerance or depth >= MAX_BEZIER_DEPTH:
        return [(segment.end.x, segment.end.y)]

    left, right = _split_bezier(segment)
    return (
        _flatten_bezier(left, tolerance / 2.0, depth + 1)
        + _flatten_bezier(right, tolerance / 2.0, depth + 1)
    )


def _ring_coordinates(segments):
    if not segments:
        return []

    first = segments[0].start
    coordinates = [(first.x, first.y)]

    for segment in segments:
        if isinstance(segment, Line):
            coordinates.append((segment.end.x, segment.end.y))
        elif isinstance(segment, Bezier):
            coordinates.extend(_flatten_bezier(segment))

    if len(coordinates) >= 2 and coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])
    return coordinates


def _signed_ring_area(coordinates) -> float:
    if len(coordinates) < 4:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(coordinates, coordinates[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _filled_path_area(path) -> float | None:
    """
    Measure a processed black-fill path.

    LaserPrep's black-engraving stage emits one polygon per Path, with
    its exterior ring first and any interior rings (holes) afterwards.
    """
    rings = _split_subpaths(path.segments)
    if not rings:
        return None

    areas = [abs(_signed_ring_area(_ring_coordinates(ring))) for ring in rings]
    if not areas or areas[0] <= 0:
        return None

    return max(0.0, areas[0] - sum(areas[1:]))


def analyse_drawing(drawing) -> CutTimeGeometry:
    """
    Measure blue cutting, green/red vector engraving and black fill.

    Measurements are taken from Drawing.paths after LaserPrep's normal
    cleanup and black-fill processing. Colours are exact official palette
    RGB values; near-colours should already have been normalized upstream.
    """
    result = CutTimeGeometry()

    for path in getattr(drawing, "paths", []):
        segments = list(path)
        if not segments:
            continue

        stroke_color = getattr(path, "stroke_color", None)
        stroke_enabled = getattr(path, "stroke_enabled", stroke_color is not None)

        if stroke_enabled and stroke_color in (BLUE, GREEN, RED):
            if stroke_color == BLUE:
                result.blue_paths += 1
                straight_attr = "cut_straight_length_mm"
                curve_attr = "cut_curve_length_mm"
                segment_attr = "blue_segments"
            elif stroke_color == GREEN:
                result.green_paths += 1
                straight_attr = "green_engrave_straight_length_mm"
                curve_attr = "green_engrave_curve_length_mm"
                segment_attr = "green_segments"
            else:
                result.red_paths += 1
                straight_attr = "red_engrave_straight_length_mm"
                curve_attr = "red_engrave_curve_length_mm"
                segment_attr = "red_segments"

            for segment in segments:
                if isinstance(segment, Line):
                    setattr(
                        result,
                        straight_attr,
                        getattr(result, straight_attr) + segment_length(segment),
                    )
                    setattr(result, segment_attr, getattr(result, segment_attr) + 1)
                elif isinstance(segment, Bezier):
                    setattr(
                        result,
                        curve_attr,
                        getattr(result, curve_attr) + segment_length(segment),
                    )
                    setattr(result, segment_attr, getattr(result, segment_attr) + 1)

        if (
            getattr(path, "fill_enabled", False)
            and getattr(path, "fill_color", None) == BLACK
        ):
            result.black_fill_paths += 1
            result.black_fill_segments += len(segments)
            area = _filled_path_area(path)
            if area is None:
                result.black_fill_unmeasurable_paths += 1
            else:
                result.black_fill_area_mm2 += area

    return result
