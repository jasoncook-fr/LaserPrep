"""
topology.py

Reconstruct topological paths from imported geometry.

Version 0.2

Topology rebuilds stroke geometry, but preserves imported paths that carry
meaningful fill information (for example filled PDF artwork) and imported
closed black artwork strokes whose original width must be retained.
"""

from collections import defaultdict

from drawing import Drawing, Line, Bezier, Path


# ============================================================
# Helpers
# ============================================================

def point_key(point):
    """
    Convert a Point into a hashable key.

    Coordinates are rounded to avoid tiny floating-point
    differences preventing endpoint matching.
    """

    return (
        round(point.x, 3),
        round(point.y, 3),
    )


def _path_geometry_key(path):
    """
    Return a direction-independent geometry key for an imported Path.

    This is used only to recognize an exact black fill / black stroke
    boundary pair.  It does not merge ordinary geometry.
    """

    signatures = []

    for segment in path:
        if isinstance(segment, Line):
            p1 = (
                round(segment.start.x, 3),
                round(segment.start.y, 3),
            )
            p2 = (
                round(segment.end.x, 3),
                round(segment.end.y, 3),
            )

            if p1 <= p2:
                signatures.append(("L", p1, p2))
            else:
                signatures.append(("L", p2, p1))

        elif isinstance(segment, Bezier):
            p1 = (
                round(segment.start.x, 3),
                round(segment.start.y, 3),
            )
            c1 = (
                round(segment.control1.x, 3),
                round(segment.control1.y, 3),
            )
            c2 = (
                round(segment.control2.x, 3),
                round(segment.control2.y, 3),
            )
            p2 = (
                round(segment.end.x, 3),
                round(segment.end.y, 3),
            )

            forward = ("B", p1, c1, c2, p2)
            reverse = ("B", p2, c2, c1, p1)
            signatures.append(min(forward, reverse))

    return tuple(sorted(signatures))


def _preserved_imported_paths(drawing):
    """
    Preserve imported engraving artwork.

    Black fills are engraving fills. Black strokes are also engraving
    artwork and retain their effective source stroke width.

    If a black stroke is an exact geometric duplicate of a black fill
    boundary, the redundant stroke is suppressed. The fill already
    engraves that region, so retaining the boundary stroke would cause
    an unnecessary second engraving pass around its edge.

    Other black strokes are preserved normally.
    """

    preserved = []
    black_fill_geometry = set()

    # First identify the geometry of all imported black fills.
    for path in drawing.paths:
        if getattr(path, "fill_color", None) == (0, 0, 0):
            black_fill_geometry.add(_path_geometry_key(path))

    for path in drawing.paths:
        if getattr(path, "is_text", False):
            preserved.append(path)
            continue

        if getattr(path, "fill_color", None) is not None:
            preserved.append(path)
            continue

        if getattr(path, "stroke_color", None) == (0, 0, 0):
            geometry_key = _path_geometry_key(path)

            if geometry_key in black_fill_geometry:
                # This is the redundant contour of an existing black fill.
                # Mark its segments so build_paths() will not reconstruct
                # them as a separate engraving path.
                for segment in path:
                    segment._suppress_from_topology = True
                continue

            path.preserve_stroke_width = True
            preserved.append(path)

    return preserved


# ============================================================
# Public
# ============================================================
def _same_style(a, b):
    """Return True if two primitives can belong to the same SVG path."""
    return (
        a.stroke_color == b.stroke_color
        and a.stroke_width == b.stroke_width
        and getattr(a, "stroke_enabled", True) == getattr(b, "stroke_enabled", True)
        and getattr(a, "fill_enabled", False) == getattr(b, "fill_enabled", False)
        and getattr(a, "fill_color", None) == getattr(b, "fill_color", None)
    )

def _order_component(component, lines):
    """
    Return the component as separate, style-consistent traversal chains.

    Every input line is consumed exactly once.  Lines are only joined when
    they have the same stroke style, so different laser colors never share
    one output Path.
    """

    adjacency = defaultdict(list)

    for idx in component:
        line = lines[idx]
        adjacency[point_key(line.start)].append(idx)
        adjacency[point_key(line.end)].append(idx)

    chains = []
    remaining = set(component)

    while remaining:
        # Prefer a remaining line at an endpoint. This gives ordinary open
        # geometry a natural traversal direction.
        start = None

        for key, members in adjacency.items():
            candidates = [idx for idx in members if idx in remaining]
            if len(candidates) == 1:
                start = candidates[0]
                break

        # Closed loops, or components with no degree-1 endpoint.
        if start is None:
            start = next(iter(remaining))

        chain = []
        current = start
        current_point = None

        while current in remaining:
            chain.append(current)
            remaining.remove(current)

            line = lines[current]

            if current_point is None:
                current_point = point_key(line.end)
            elif point_key(line.start) == current_point:
                current_point = point_key(line.end)
            else:
                current_point = point_key(line.start)

            next_line = None

            for candidate in adjacency[current_point]:
                if candidate not in remaining:
                    continue

                if not _same_style(lines[current], lines[candidate]):
                    continue

                next_line = candidate
                break

            if next_line is None:
                break

            current = next_line

        if chain:
            chains.append(chain)

    return chains


def build_paths(drawing: Drawing) -> None:
    """
    Build topological Path objects from drawing.objects.

    Imported filled artwork and selected closed circular artwork strokes
    are preserved. Ordinary stroke geometry is rebuilt as before.
    """

    preserved = _preserved_imported_paths(drawing)

    drawing.paths.clear()
    drawing.paths.extend(preserved)

    preserved_segments = {
        id(segment)
        for path in preserved
        for segment in path
    }

    lines = []
    beziers = []

    for obj in drawing.objects:

        # Imported artwork already preserved as complete Paths, and any
        # explicitly suppressed redundant black contours, must not be
        # reconstructed as ordinary stroke geometry.
        if id(obj) in preserved_segments:
            continue

        if getattr(obj, "_suppress_from_topology", False):
            continue

        if isinstance(obj, Line):
            lines.append(obj)

        elif isinstance(obj, Bezier):
            beziers.append(obj)

    # Preserve Beziers as individual stroke paths.
    for bezier in beziers:

        path = Path()

        path.add(bezier)

        path.stroke_color = bezier.stroke_color
        path.stroke_width = bezier.stroke_width
        path.import_order = bezier.import_order

        drawing.paths.append(path)

    # Build endpoint graph.
    adjacency = defaultdict(list)

    for index, line in enumerate(lines):

        adjacency[point_key(line.start)].append(index)
        adjacency[point_key(line.end)].append(index)

    # Discover connected components.
    visited = set()

    for start in range(len(lines)):

        if start in visited:
            continue

        stack = [start]
        component = []

        while stack:

            current = stack.pop()

            if current in visited:
                continue

            visited.add(current)
            component.append(current)

            line = lines[current]

            for endpoint in (
                point_key(line.start),
                point_key(line.end),
            ):

                for neighbour in adjacency[endpoint]:

                    if neighbour not in visited:
                        stack.append(neighbour)

        chains = _order_component(component, lines)

        for chain in chains:
            if not chain:
                continue

            first = lines[chain[0]]

            path = Path()
            path.stroke_color = first.stroke_color
            path.stroke_width = first.stroke_width
            path.import_order = first.import_order

            for index in chain:
                path.add(lines[index])

            drawing.paths.append(path)

    print()
    print("Topology")
    print("-------------------------------------")
    print(f"Objects : {len(drawing.objects)}")
    print(f"Paths   : {len(drawing.paths)}")
