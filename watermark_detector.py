"""
watermark_detector.py

Detects watermark text groups.

This module never modifies geometry.
It only identifies suspicious TextGroups.
"""

from __future__ import annotations

from text_group_analysis import TextGroup


#
# Detection thresholds
#
MIN_GLYPHS = 12

MAX_HEIGHT_MM = 1.50

MIN_WIDTH_MM = 8.0

PAGE_MARGIN_MM = 20.0


def _score(
    group: TextGroup,
    page_width: float,
    page_height: float,
) -> int:
    """
    Returns a confidence score.
    """

    score = 0

    #
    # Watermarks usually contain many glyphs.
    #
    if len(group.paths) >= MIN_GLYPHS:
        score += 2

    #
    # Very small text.
    #
    if group.height <= MAX_HEIGHT_MM:
        score += 3

    #
    # Long enough to be a word.
    #
    if group.width >= MIN_WIDTH_MM:
        score += 1

    #
    # Close to page edge.
    #
    left = group.left
    right = page_width - group.right
    top = group.top
    bottom = page_height - group.bottom

    nearest = min(left, right, top, bottom)

    if nearest <= PAGE_MARGIN_MM:
        score += 1

    return score


def find_watermark_groups(
    groups: list[TextGroup],
    page_width: float,
    page_height: float,
    minimum_score: int = 6,
) -> list[TextGroup]:
    """
    Returns groups that are likely to be watermarks.
    """

    matches = []

    for group in groups:

        score = _score(
            group,
            page_width,
            page_height,
        )

        if score >= minimum_score:
            matches.append(group)

    return matches
