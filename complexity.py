"""
complexity.py

Complexity analysis for LaserPrep.

This module evaluates the overall complexity of an imported drawing
and determines whether processing should continue.
"""

from dataclasses import dataclass

from config import (
    COMPLEXITY_WARNING_OBJECTS,
    COMPLEXITY_HIGH_OBJECTS,
    COMPLEXITY_ABORT_OBJECTS,
)


@dataclass
class Complexity:
    object_count: int
    rating: str
    should_abort: bool


def analyse_complexity(drawing) -> Complexity:
    """
    Analyse drawing complexity based on the number of imported objects.
    """

    object_count = len(drawing.objects)

    if object_count >= COMPLEXITY_ABORT_OBJECTS:
        return Complexity(
            object_count=object_count,
            rating="ABORT",
            should_abort=True,
        )

    if object_count >= COMPLEXITY_HIGH_OBJECTS:
        return Complexity(
            object_count=object_count,
            rating="HIGH",
            should_abort=False,
        )

    if object_count >= COMPLEXITY_WARNING_OBJECTS:
        return Complexity(
            object_count=object_count,
            rating="WARNING",
            should_abort=False,
        )

    return Complexity(
        object_count=object_count,
        rating="NORMAL",
        should_abort=False,
    )
