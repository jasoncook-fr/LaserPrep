"""Conservative support for simple SVG clip paths during geometry import.

Only simple convex polygon clips are considered. Unsupported clipping constructs
are deliberately ignored rather than approximated.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from drawing import Line, Bezier
from svg_path_parser import parse_svg_path
from svg_transform import AffineTransform

SVG_NS = "{http://www.w3.org/2000/svg}"
CLIP_URL_RE = re.compile(r"url\(\s*['\"]?#([^)\s'\"]+)['\"]?\s*\)")
EPSILON = 1e-7


def _tag(element):
    return element.tag.split("}", 1)[-1]


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _convex_hull(points):
    points = sorted(set((float(x), float(y)) for x, y in points))
    if len(points) <= 1:
        return points

    lower = []
    for point in points:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= EPSILON:
            lower.pop()
        lower.append(point)

    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= EPSILON:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _is_convex_polygon(points):
    if len(points) < 3:
        return False
    signs = []
    for i in range(len(points)):
        value = _cross(points[i], points[(i + 1) % len(points)], points[(i + 2) % len(points)])
        if abs(value) > EPSILON:
            signs.append(value > 0)
    return bool(signs) and all(sign == signs[0] for sign in signs)


def _point_on_segment(point, a, b):
    if abs(_cross(a, b, point)) > EPSILON:
        return False
    return (
        min(a[0], b[0]) - EPSILON <= point[0] <= max(a[0], b[0]) + EPSILON
        and min(a[1], b[1]) - EPSILON <= point[1] <= max(a[1], b[1]) + EPSILON
    )


def _segments_intersect(a, b, c, d):
    o1, o2 = _cross(a, b, c), _cross(a, b, d)
    o3, o4 = _cross(c, d, a), _cross(c, d, b)

    if ((o1 > EPSILON and o2 < -EPSILON) or (o1 < -EPSILON and o2 > EPSILON)) and (
        (o3 > EPSILON and o4 < -EPSILON) or (o3 < -EPSILON and o4 > EPSILON)
    ):
        return True

    return (
        _point_on_segment(c, a, b)
        or _point_on_segment(d, a, b)
        or _point_on_segment(a, c, d)
        or _point_on_segment(b, c, d)
    )


def _point_in_polygon(point, polygon):
    # Even-odd ray casting. Boundary points count as inside.
    inside = False
    x, y = point

    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]

        if _point_on_segment(point, a, b):
            return True

        if (a[1] > y) != (b[1] > y):
            x_cross = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x_cross > x:
                inside = not inside

    return inside


def _polygon_edges(points):
    if len(points) == 2:
        return [(points[0], points[1])]
    if len(points) < 2:
        return []
    return [(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]


def _is_simple_polygon(points):
    if len(points) < 3:
        return False

    edges = _polygon_edges(points)
    count = len(edges)

    for i, (a, b) in enumerate(edges):
        for j in range(i + 1, count):
            if j == i + 1 or (i == 0 and j == count - 1):
                continue
            if _segments_intersect(a, b, *edges[j]):
                return False

    return True


def _polygons_disjoint(a, b):
    # Touching or intersecting boundaries are retained.
    if not a or len(b) < 3:
        return False

    for edge_a in _polygon_edges(a):
        for edge_b in _polygon_edges(b):
            if _segments_intersect(*edge_a, *edge_b):
                return False

    if len(a) >= 3 and _point_in_polygon(b[0], a):
        return False

    if _point_in_polygon(a[0], b):
        return False

    return True


def _projection(poly, axis):
    values = [p[0] * axis[0] + p[1] * axis[1] for p in poly]
    return min(values), max(values)


def _has_separating_axis(a, b):
    # Include both edge normals and edge directions. The latter also make the
    # test valid when the geometry hull degenerates to a line segment.
    for polygon in (a, b):
        if len(polygon) < 2:
            continue
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            for axis in ((-dy, dx), (dx, dy)):
                if abs(axis[0]) + abs(axis[1]) <= EPSILON:
                    continue
                amin, amax = _projection(a, axis)
                bmin, bmax = _projection(b, axis)
                if amax < bmin - EPSILON or bmax < amin - EPSILON:
                    return True
    return False


def _segment_points(path):
    points = []
    for segment in path:
        if isinstance(segment, Line):
            points.extend(((segment.start.x, segment.start.y), (segment.end.x, segment.end.y)))
        elif isinstance(segment, Bezier):
            # A cubic Bezier is contained by the convex hull of these four points.
            points.extend((
                (segment.start.x, segment.start.y),
                (segment.control1.x, segment.control1.y),
                (segment.control2.x, segment.control2.y),
                (segment.end.x, segment.end.y),
            ))
    return points


def _clip_polygon(clip_element):
    if clip_element.attrib.get("transform"):
        return None

    children = [child for child in clip_element if _tag(child) not in ("title", "desc")]
    if len(children) != 1 or _tag(children[0]) != "path":
        return None

    node = children[0]
    if node.attrib.get("clip-path") or node.attrib.get("fill-rule", "nonzero") == "evenodd":
        return None

    clip_rule = node.attrib.get("clip-rule", "nonzero").strip().lower()

    transform_text = node.attrib.get("transform", "")
    try:
        transform = AffineTransform.from_svg(transform_text)
        parsed = parse_svg_path(node.attrib.get("d", ""))[0]
    except Exception:
        return None

    if not parsed.objects or any(not isinstance(obj, Line) for obj in parsed):
        return None

    parsed.objects = [transform.apply(obj) for obj in parsed.objects]
    points = [(obj.start.x, obj.start.y) for obj in parsed]

    # SVG clip paths are implicitly closed, even without a Z command.
    # MuPDF often repeats the starting coordinate instead.
    final_point = (
        parsed.objects[-1].end.x,
        parsed.objects[-1].end.y,
    )
    if (
        abs(final_point[0] - points[0][0]) > EPSILON
        or abs(final_point[1] - points[0][1]) > EPSILON
    ):
        points.append(final_point)
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()

    # Remove adjacent duplicate vertices without changing the polygon.
    clean = []
    for point in points:
        if not clean or point != clean[-1]:
            clean.append(point)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()

    # Accept simple concave polygons, and self-intersecting polygons only
    # when their clipping rule explicitly specifies even-odd semantics.
    if _is_simple_polygon(clean) or clip_rule == "evenodd":
        return clean
    return None


def _clip_ids(value):
    if not value:
        return []
    return CLIP_URL_RE.findall(value)


def should_discard_path(root, node, transformed_path, clip_cache=None):
    """Return True only when a path is provably wholly outside an active clip.

    Group transforms and unsupported/malformed clips cause a conservative keep.
    ``transformed_path`` must already have the path element's own transform
    applied, matching the coordinate space used by the imported geometry.
    """
    if clip_cache is None:
        clip_cache = {}

    parent_map = {child: parent for parent in root.iter() for child in parent}
    ancestors = []
    current = node
    while current is not None:
        ancestors.append(current)
        current = parent_map.get(current)

    # Group/root transforms are not yet handled by the importer itself. Do not
    # make clipping decisions in a coordinate system we cannot establish.
    for ancestor in ancestors[1:]:
        if ancestor.attrib.get("transform"):
            return False

    ids = []
    for ancestor in ancestors:
        ids.extend(_clip_ids(ancestor.attrib.get("clip-path")))
    if not ids:
        return False

    definitions = {
        element.attrib.get("id"): element
        for element in root.iter()
        if _tag(element) == "clipPath" and element.attrib.get("id")
    }

    geometry_hull = _convex_hull(_segment_points(transformed_path))
    if not geometry_hull:
        return False

    for clip_id in ids:
        if clip_id not in clip_cache:
            clip = definitions.get(clip_id)
            clip_cache[clip_id] = _clip_polygon(clip) if clip is not None else None

        polygon = clip_cache[clip_id]
        if polygon is None:
            continue

        if _polygons_disjoint(geometry_hull, polygon):
            return True

    return False
