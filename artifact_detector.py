"""
artifact_detector.py

High-level artifact detection.

This module combines the results of the individual artifact
detectors into a single list of TextGroups to remove.
"""

from __future__ import annotations

from text_group_analysis import TextGroup
from watermark_detector import find_watermark_groups

# ----------------------------------------------------------------------
# Software stamp detector
# ----------------------------------------------------------------------

def find_software_stamp_groups(
    groups: list[TextGroup],
    page_width: float,
    page_height: float,
) -> list[TextGroup]:
    """
    Detect visible software-generated stamps.

    Initial implementation targets the ARCHICAD education stamp.

    The detector is intentionally conservative.
    """

    matches = []

    for group in groups:

        #
        # Direct vector text only.
        #
        if not all(getattr(path, "is_direct_text", False) for path in group.paths):
            continue

        glyphs = len(group.paths)

        #
        # ARCHICAD VERSION EDUCATION
        #
        if (
            23 <= glyphs <= 25
            and 60.0 <= group.width <= 70.0
            and 2.5 <= group.height <= 3.5
        ):
            matches.append(group)

    return matches


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

def find_artifact_groups(
    groups: list[TextGroup],
    page_width: float,
    page_height: float,
) -> list[TextGroup]:
    """
    Returns every detected artifact group.
    """

    artifacts = []

    #
    # Hidden semantic watermark.
    #
    artifacts.extend(
        find_watermark_groups(
            groups,
            page_width,
            page_height,
        )
    )

    #
    # Visible software-generated vector stamps.
    #
    artifacts.extend(
        find_software_stamp_groups(
            groups,
            page_width,
            page_height,
        )
    )

    #
    # Remove duplicates while preserving order.
    #
    seen = set()
    unique = []

    for group in artifacts:

        key = id(group)

        if key in seen:
            continue

        seen.add(key)
        unique.append(group)

    return unique




