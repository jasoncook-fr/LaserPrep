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


def _preserved_imported_paths(drawing):
    """
    Preserve all imported black engraving artwork.

    Black fills are engraving fills. Black strokes are also engraving
    artwork and retain their effective source stroke width. Other colors
    continue through the normal topology/hairline pipeline.
    """

    preserved = []

    for path in drawing.paths:
        if getattr(path, "is_text", False):
            preserved.append(path)
            continue

        if getattr(path, "fill_color", None) is not None:
            preserved.append(path)
            continue

        if getattr(path, "stroke_color", None) == (0, 0, 0):
            path.preserve_stroke_width = True
            preserved.append(path)

    return preserved


# ============================================================
# Public
# ============================================================

def _order_component(component, lines):
    """
    Return the line indices in traversal order.
    """

    adjacency = defaultdict(list)

    for idx in component:
        line = lines[idx]
        adjacency[point_key(line.start)].append(idx)
        adjacency[point_key(line.end)].append(idx)

    start = None

    for key, members in adjacency.items():
        if len(members) == 1:
            start = members[0]
            break

    if start is None:
        start = component[0]

    ordered = []
    visited = set()

    current = start
    current_point = None

    while True:

        ordered.append(current)
        visited.add(current)

        line = lines[current]

        if current_point is None:
            current_point = point_key(line.end)

        else:
            if point_key(line.start) == current_point:
                current_point = point_key(line.end)
            else:
                current_point = point_key(line.start)

        next_line = None

        for candidate in adjacency[current_point]:
            if candidate not in visited:
                next_line = candidate
                break

        if next_line is None:
            break

        current = next_line

    return ordered


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

        # Filled artwork and preserved circular strokes have already been
        # kept as complete Paths. Do not reconstruct their segments.
        if id(obj) in preserved_segments:
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

        ordered = _order_component(component, lines)

        if not ordered:
            continue

        first = lines[ordered[0]]

        path = Path()
        path.stroke_color = first.stroke_color
        path.stroke_width = first.stroke_width
        path.import_order = first.import_order

        for index in ordered:
            path.add(lines[index])

        drawing.paths.append(path)

    print()
    print("Topology")
    print("-------------------------------------")
    print(f"Objects : {len(drawing.objects)}")
    print(f"Paths   : {len(drawing.paths)}")
