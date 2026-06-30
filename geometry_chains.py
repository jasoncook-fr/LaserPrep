"""
geometry_chains.py

Analyse connected chains of line segments.

Version 0.8.1
"""

from collections import defaultdict
from drawing import Drawing, Line


# ============================================================
# REPORT
# ============================================================

class ChainStatistics:

    def __init__(self):

        self.total_chains = 0

        self.longest_chain = 0
        self.total_segments = 0

        self.one = 0
        self.two_to_five = 0
        self.six_to_twenty = 0
        self.twentyone_to_hundred = 0
        self.over_hundred = 0


# ============================================================
# HELPERS
# ============================================================

def point_key(point):

    return (
        round(point.x, 3),
        round(point.y, 3),
    )


# ============================================================
# ANALYSIS
# ============================================================

def analyse(drawing: Drawing):

    stats = ChainStatistics()

    adjacency = defaultdict(list)

    lines = []

    # ------------------------------------
    # Build graph
    # ------------------------------------

    for obj in drawing.objects:
        if not isinstance(obj, Line):
            continue

        index = len(lines)

        lines.append(obj)

        a = point_key(obj.start)
        b = point_key(obj.end)

        adjacency[a].append(index)
        adjacency[b].append(index)

    visited = set()

    # ------------------------------------
    # Walk every chain
    # ------------------------------------

    for start in range(len(lines)):

        if start in visited:
            continue

        count = 0

        stack = [start]

        while stack:

            current = stack.pop()

            if current in visited:
                continue

            visited.add(current)

            count += 1

            line = lines[current]

            for pt in (
                point_key(line.start),
                point_key(line.end),
            ):

                for neighbour in adjacency[pt]:

                    if neighbour not in visited:
                        stack.append(neighbour)

        stats.total_chains += 1
        stats.total_segments += count

        stats.longest_chain = max(
            stats.longest_chain,
            count,
        )

        if count == 1:
            stats.one += 1

        elif count <= 5:
            stats.two_to_five += 1

        elif count <= 20:
            stats.six_to_twenty += 1

        elif count <= 100:
            stats.twentyone_to_hundred += 1

        else:
            stats.over_hundred += 1

    return stats
