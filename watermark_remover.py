"""
watermark_remover.py

Removes VectorPaths belonging to detected watermark groups.
"""

from __future__ import annotations

from vector_path import VectorPath
from text_group_analysis import TextGroup


def remove_watermarks(
    paths: list[VectorPath],
    watermark_groups: list[TextGroup],
) -> list[VectorPath]:
    """
    Returns a new list of VectorPaths with watermark paths removed.
    """

    remove_indices = set()

    for group in watermark_groups:
        remove_indices.update(group.path_indices)

    return [
        path
        for index, path in enumerate(paths)
        if index not in remove_indices
    ]
