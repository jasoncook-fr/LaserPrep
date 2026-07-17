"""
topology.py

Reconstruct topological paths from imported geometry.

Version 0.2
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


# ============================================================
# Public
# ============================================================


def _walk_path(start_edge, start_vertex, edge_lookup, adjacency, lines, used):
    """
    Walk a maximal non-branching path.
    """
    ordered = []
    current_edge = start_edge
    current_vertex = start_vertex

    while True:
        used.add(current_edge)
        ordered.append(current_edge)

        line = lines[current_edge]
        a = point_key(line.start)
        b = point_key(line.end)
        next_vertex = b if current_vertex == a else a

        if len(adjacency[next_vertex]) != 2:
            break

        nxt = None
        for edge in adjacency[next_vertex]:
            if edge != current_edge and edge not in used:
                nxt = edge
                break

        if nxt is None:
            break

        current_edge = nxt
        current_vertex = next_vertex

    return ordered




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
    Edge-centric decomposition. Every edge is emitted exactly once.
    """
    adjacency = defaultdict(list)

    for idx in component:
        line = lines[idx]
        adjacency[point_key(line.start)].append(idx)
        adjacency[point_key(line.end)].append(idx)

    used = set()
    paths = []

    def extend(edge_idx, vertex):
        out = []
        current_edge = edge_idx
        current_vertex = vertex

        while True:
            if current_edge in used:
                break

            used.add(current_edge)
            out.append(current_edge)

            line = lines[current_edge]
            a = point_key(line.start)
            b = point_key(line.end)
            nxt_vertex = b if current_vertex == a else a

            if len(adjacency[nxt_vertex]) != 2:
                break

            nxt_edge = None
            for e in adjacency[nxt_vertex]:
                if e == current_edge or e in used:
                    continue
                if not _same_style(lines[current_edge], lines[e]):
                    continue
                nxt_edge = e
                break

            if nxt_edge is None:
                break

            current_edge = nxt_edge
            current_vertex = nxt_vertex

        return out

    for edge in component:
        if edge in used:
            continue

        line = lines[edge]
        a = point_key(line.start)
        b = point_key(line.end)

        left = list(reversed(extend(edge, a)))
        if left:
            left = left[:-1]  # remove duplicated seed edge

        right = []
        if edge not in used:
            right = extend(edge, b)
        else:
            right = [edge] + extend(edge, b)

        path = left + right
        if path:
            paths.append(path)

    return paths

def build_paths(drawing: Drawing) -> None:
    """
    Build topological Path objects from drawing.objects.

    This function populates drawing.paths while leaving
    drawing.objects completely untouched.
    """

    drawing.paths.clear()

    lines = []
    beziers = []

    for obj in drawing.objects:

        if isinstance(obj, Line):
            lines.append(obj)

        elif isinstance(obj, Bezier):
            beziers.append(obj)

    #
    # Preserve Beziers for now.
    #

    for bezier in beziers:

        path = Path()

        path.add(bezier)

        path.stroke_color = bezier.stroke_color
        path.stroke_width = bezier.stroke_width
        path.import_order = bezier.import_order

        drawing.paths.append(path)

    #
    # Build endpoint graph.
    #

    adjacency = defaultdict(list)

    for index, line in enumerate(lines):

        adjacency[point_key(line.start)].append(index)
        adjacency[point_key(line.end)].append(index)

    #
    # Discover connected components.
    #

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

        #
        # Version 0.2
        #
        # The component is NOT ordered yet.
        #
        # We simply create one Path containing all
        # connected Line objects.
        #

        ordered_paths = _order_component(component, lines)

        for ordered in ordered_paths:
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


