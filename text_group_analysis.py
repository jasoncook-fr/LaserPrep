"""
text_group_analysis.py

Groups imported text glyphs into logical text groups.
"""

from __future__ import annotations

from dataclasses import dataclass

from drawing import Point
from vector_path import VectorPath


@dataclass(slots=True)
class TextGroup:
    """
    One connected group of nearby text glyphs.
    """

    path_indices: list[int]
    paths: list[VectorPath]

    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def centre(self) -> Point:
        return Point(
            (self.left + self.right) / 2,
            (self.top + self.bottom) / 2,
        )


def _close(a: VectorPath, b: VectorPath) -> bool:
    """
    Returns True if two glyphs are considered neighbours.
    """

    X_DISTANCE = 8.0
    Y_DISTANCE = 1.5

    return (
        abs(a.center.x - b.center.x) <= X_DISTANCE
        and
        abs(a.center.y - b.center.y) <= Y_DISTANCE
    )


def group_text_paths(
    paths: list[VectorPath],
    distance: float = 4.0,
) -> list[TextGroup]:
    """
    Groups nearby text glyphs.

    Only VectorPaths with is_text == True are considered.
    """

    text_paths = [
        (index, path)
        for index, path in enumerate(paths)
        if getattr(path, "is_text", False)
    ]

    groups: list[TextGroup] = []
    visited: set[int] = set()

    for start_index, start_path in text_paths:

        if start_index in visited:
            continue

        queue = [(start_index, start_path)]

        visited.add(start_index)

        members = []

        while queue:

            current_index, current = queue.pop()

            members.append((current_index, current))

            for other_index, other in text_paths:

                if other_index in visited:
                    continue

                if _close(current, other):
                    visited.add(other_index)
                    queue.append((other_index, other))

        left = min(path.bounds[0] for _, path in members)
        top = min(path.bounds[1] for _, path in members)
        right = max(path.bounds[2] for _, path in members)
        bottom = max(path.bounds[3] for _, path in members)

        groups.append(
            TextGroup(
                path_indices=[i for i, _ in members],
                paths=[p for _, p in members],
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            )
        )

    groups.sort(
        key=lambda g: len(g.paths),
        reverse=True,
    )

    return groups
