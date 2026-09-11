"""
Black engraving cleanup for LaserPrep.

Black artwork is treated as engraving geometry rather than as ordinary
contour geometry.  Black filled paths are boolean-unioned, white filled
geometry is used as a transparent knockout, and redundant black strokes
are not involved in the engraving result.

The important detail here is that one SVG path may contain several
subpaths (for example, the outside and the hole of an O).  Each subpath
is converted to its own ring before any Shapely operation is performed.
"""

from __future__ import annotations

from typing import Iterable

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.ops import unary_union

from drawing import Line, Bezier, Path, Point


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CURVE_STEPS = 32
AREA_EPSILON = 1e-9


def _is_black(path: Path) -> bool:
    return path.fill_color == BLACK


def _is_white(path: Path) -> bool:
    return path.fill_color == WHITE


def _point_equal(a: Point, b: Point, eps: float = 1e-7) -> bool:
    return abs(a.x - b.x) <= eps and abs(a.y - b.y) <= eps


def _cubic(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    mt = 1.0 - t
    return Point(
        mt**3 * p0.x
        + 3 * mt**2 * t * p1.x
        + 3 * mt * t**2 * p2.x
        + t**3 * p3.x,
        mt**3 * p0.y
        + 3 * mt**2 * t * p1.y
        + 3 * mt * t**2 * p2.y
        + t**3 * p3.y,
    )


def _split_subpaths(path: Path) -> list[list[Line | Bezier]]:
    """Split one Path wherever SVG would start a new subpath."""

    rings: list[list[Line | Bezier]] = []
    current: list[Line | Bezier] = []
    previous_end: Point | None = None

    for segment in path:
        if previous_end is not None and not _point_equal(segment.start, previous_end):
            if current:
                rings.append(current)
            current = []

        current.append(segment)
        previous_end = segment.end

    if current:
        rings.append(current)

    return rings


def _sample_ring(segments: Iterable[Line | Bezier]) -> list[tuple[float, float]]:
    """Turn one subpath into a polygon ring, approximating Beziers."""

    points: list[tuple[float, float]] = []
    first_start: Point | None = None

    for segment in segments:
        if first_start is None:
            first_start = segment.start
            points.append((segment.start.x, segment.start.y))

        if isinstance(segment, Line):
            points.append((segment.end.x, segment.end.y))
            continue

        for i in range(1, CURVE_STEPS + 1):
            p = _cubic(
                segment.start,
                segment.control1,
                segment.control2,
                segment.end,
                i / CURVE_STEPS,
            )
            points.append((p.x, p.y))

    if len(points) >= 2 and points[0] != points[-1]:
        points.append(points[0])

    return points


def _path_geometry(path: Path):
    """
    Convert one filled SVG/LaserPrep Path to Shapely geometry.

    Multiple rings in a single source path are combined using symmetric
    difference, matching SVG's even-odd fill rule used by LaserPrep's
    writer.  This is what preserves glyph holes and compound artwork.
    """

    geometry = None

    for subpath in _split_subpaths(path):
        coords = _sample_ring(subpath)
        if len(coords) < 4:
            continue

        polygon = Polygon(coords)
        if polygon.is_empty or polygon.area <= AREA_EPSILON:
            continue

        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        if polygon.is_empty:
            continue

        geometry = polygon if geometry is None else geometry.symmetric_difference(polygon)

    return geometry


def _polygon_parts(geometry):
    """Yield every Polygon contained in an arbitrary Shapely geometry."""

    if geometry is None or geometry.is_empty:
        return

    if isinstance(geometry, Polygon):
        yield geometry
        return

    if isinstance(geometry, MultiPolygon):
        yield from geometry.geoms
        return

    if isinstance(geometry, GeometryCollection):
        for item in geometry.geoms:
            yield from _polygon_parts(item)


def _ring_segments(coords, import_order: int) -> list[Line]:
    """Create line segments for one closed polygon ring."""

    points = [Point(float(x), float(y)) for x, y in coords]
    segments: list[Line] = []

    for start, end in zip(points, points[1:]):
        segments.append(
            Line(
                start=start,
                end=end,
                stroke_color=BLACK,
                stroke_width=0.01,
                import_order=import_order,
            )
        )

    return segments


def _path_from_polygon(polygon: Polygon, import_order: int) -> Path:
    """
    Convert a Shapely Polygon to one LaserPrep Path.

    The writer emits an M whenever there is a discontinuity between
    segments and uses even-odd fill, so exterior + interior rings can live
    safely in the same Path.
    """

    segments: list[Line] = []
    segments.extend(_ring_segments(polygon.exterior.coords, import_order))

    for interior in polygon.interiors:
        segments.extend(_ring_segments(interior.coords, import_order))

    return Path(
        segments=segments,
        closed=True,
        stroke_color=None,
        fill_color=BLACK,
        stroke_width=0.01,
        stroke_enabled=False,
        fill_enabled=True,
        is_text=False,
        import_order=import_order,
    )


def _remove_white_paint(paths: list[Path]) -> None:
    """Make pure-white fills/strokes transparent everywhere."""

    for path in paths:
        if path.fill_color == WHITE:
            path.fill_color = None
            path.fill_enabled = False

        if path.stroke_color == WHITE:
            path.stroke_color = None
            path.stroke_enabled = False


def process_black_engraving(drawing) -> dict[str, int]:
    """
    Replace black engraving artwork with clean boolean geometry.

    Text paths explicitly marked as ``is_text`` are left untouched.  This
    is deliberately not the only text protection: vectorized PDF text is
    often imported as ordinary filled geometry, so compound-path handling
    must itself be correct.
    """

    original_paths = list(drawing.paths)

    black_paths = [
        path
        for path in original_paths
        if _is_black(path) and not getattr(path, "is_text", False)
    ]

    white_paths = [
        path
        for path in original_paths
        if _is_white(path) and not getattr(path, "is_text", False)
    ]

    _remove_white_paint(original_paths)

    black_geometry = None
    for path in black_paths:
        geometry = _path_geometry(path)
        if geometry is None or geometry.is_empty:
            continue
        black_geometry = (
            geometry
            if black_geometry is None
            else black_geometry.union(geometry)
        )

    white_geometry = None
    for path in white_paths:
        geometry = _path_geometry(path)
        if geometry is None or geometry.is_empty:
            continue
        white_geometry = (
            geometry
            if white_geometry is None
            else white_geometry.union(geometry)
        )

    if black_geometry is not None and white_geometry is not None:
        black_geometry = black_geometry.difference(white_geometry)

    # Remove every processed black fill, then put the boolean result back
    # at the position of the first processed black path.  This preserves
    # paint ordering relative to unrelated coloured artwork.
    processed_ids = {id(path) for path in black_paths + white_paths}
    remaining = [path for path in original_paths if id(path) not in processed_ids]

    result_paths = list(_polygon_parts(black_geometry)) if black_geometry is not None else []
    generated = [
        _path_from_polygon(polygon, import_order=black_paths[0].import_order if black_paths else 0)
        for polygon in result_paths
        if polygon.area > AREA_EPSILON
    ]

    if black_paths:
        first_index = next(
            i for i, path in enumerate(original_paths)
            if id(path) == id(black_paths[0])
        )

        # Determine the corresponding insertion position after removing
        # the processed paths.
        insertion_index = sum(
            1 for path in original_paths[:first_index]
            if id(path) not in processed_ids
        )
        remaining[insertion_index:insertion_index] = generated
    else:
        remaining.extend(generated)

    drawing.paths = remaining

    return {
        "black_paths": len(black_paths),
        "white_paths": len(white_paths),
        "generated_paths": len(generated),
    }
