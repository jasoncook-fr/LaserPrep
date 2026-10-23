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
    COMPLEXITY_WARNING_POINTS,
    COMPLEXITY_HIGH_POINTS,
    COMPLEXITY_ABORT_POINTS,
)


@dataclass
class Complexity:
    object_count: int
    rating: str
    should_abort: bool
    point_count: int = 0

@dataclass
class PDFContent:
    raster_images: int
    vector_drawings: int
    usable_vector_drawings: int
    is_non_vector: bool

def analyse_pdf_content(page) -> PDFContent:
    """
    Determine whether a PDF page contains usable vector artwork.

    Raster images are allowed when genuine vector geometry is also present.
    A PDF is considered non-vector only when it contains raster images but
    no usable vector drawings.
    """
    raster_images = len(page.get_images(full=True))
    drawings = page.get_cdrawings()

    usable_vector_drawings = 0

    for drawing in drawings:
        items = drawing.get("items", [])

        # Ignore empty drawings and drawings with no actual geometry.
        if not items:
            continue

        # A drawing is considered useful vector content if it contains
        # line, Bézier, rectangle, or quad geometry.
        has_geometry = any(
            item[0] in ("l", "c", "qu")
            for item in items
        )

        has_stroked_geometry = (
            drawing.get("type") in ("s", "fs")
            or drawing.get("color") is not None
        )

        if has_geometry or has_stroked_geometry:
            usable_vector_drawings += 1

    return PDFContent(
        raster_images=raster_images,
        vector_drawings=len(drawings),
        usable_vector_drawings=usable_vector_drawings,
        is_non_vector=(
            raster_images > 0
            and usable_vector_drawings == 0
        ),
    )

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

def analyse_pdf_complexity(page) -> Complexity:
    """
    Analyse source PDF vector complexity before SVG export/import.
    """

    drawings = page.get_cdrawings()

    drawing_count = len(drawings)
    point_count = 0

    for drawing in drawings:
        for item in drawing.get("items", []):
            kind = item[0]

            if kind == "l":
                # Line: start + end
                point_count += 2

            elif kind == "c":
                # Cubic Bézier: 4 points
                point_count += 4

            elif kind == "re":
                # Rectangle: 4 corners
                point_count += 4

            elif kind == "qu":
                # Quad: 4 corners
                point_count += 4

            # Once the hard limit is reached, the exact count
            # is no longer important. Stop immediately.
            if point_count >= COMPLEXITY_ABORT_POINTS:
                return Complexity(
                    object_count=drawing_count,
                    rating="ABORT",
                    should_abort=True,
                    point_count=point_count,
                )

    if point_count >= COMPLEXITY_HIGH_POINTS:
        rating = "HIGH"

    elif point_count >= COMPLEXITY_WARNING_POINTS:
        rating = "WARNING"

    else:
        rating = "NORMAL"

    return Complexity(
        object_count=drawing_count,
        rating=rating,
        should_abort=False,
        point_count=point_count,
    )
