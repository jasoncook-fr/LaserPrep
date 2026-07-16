"""
artifact_analysis.py

Geometry analysis utilities used by LaserPrep diagnostics.

This module performs no filtering and no repairs.

It simply measures imported VectorPaths so that higher-level modules
can detect artifacts such as watermarks, registration marks, stray
geometry and decorative objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from drawing import Point
from vector_path import VectorPath


@dataclass(slots=True)
class GeometryMetrics:
    """
    Geometric measurements for a single VectorPath.
    """

    left: float
    top: float
    right: float
    bottom: float

    width: float
    height: float

    area: float
    aspect_ratio: float
    perimeter: float
    density: float

    centre: Point

    page_width: float
    page_height: float

    distance_left: float
    distance_right: float
    distance_top: float
    distance_bottom: float
    distance_to_edge: float

    object_count: int
    line_count: int
    bezier_count: int


def analyse_path(
    path: VectorPath,
    page_width: float,
    page_height: float,
) -> GeometryMetrics:
    """
    Calculate geometric measurements for one VectorPath.
    """

    left, top, right, bottom = path.bounds

    width = path.width
    height = path.height

    area = width * height

    if width == 0 or height == 0:
        aspect_ratio = float("inf")
    else:
        aspect_ratio = max(width, height) / min(width, height)

    perimeter = 2 * (width + height)

    density = 0.0 if area == 0 else path.object_count / area

    distance_left = left
    distance_right = page_width - right
    distance_top = top
    distance_bottom = page_height - bottom
    distance_to_edge = min(
        distance_left,
        distance_right,
        distance_top,
        distance_bottom,
    )

    return GeometryMetrics(
        left=left,
        top=top,
        right=right,
        bottom=bottom,

        width=width,
        height=height,

        area=area,
        aspect_ratio=aspect_ratio,
        perimeter=perimeter,
        density=density,

        centre=path.center,

        page_width=page_width,
        page_height=page_height,

        distance_left=distance_left,
        distance_right=distance_right,
        distance_top=distance_top,
        distance_bottom=distance_bottom,
        distance_to_edge=distance_to_edge,

        object_count=path.object_count,
        line_count=path.line_count,
        bezier_count=path.bezier_count,
    )


def analyse_paths(
    paths: list[VectorPath],
    page_width: float,
    page_height: float,
) -> list[GeometryMetrics]:
    """
    Analyse an entire collection of VectorPaths.
    """

    return [
        analyse_path(path, page_width, page_height)
        for path in paths
    ]


