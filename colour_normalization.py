"""
colour_normalization.py

Automatic colour normalisation.

Version 0.8
"""

from drawing import Drawing, Line, Bezier
from laser_palette import snap_colour


class ColourNormalizationReport:

    def __init__(self):

        self.corrected = 0


def normalize_colours(drawing: Drawing):

    report = ColourNormalizationReport()

    for obj in drawing.objects:

        if not isinstance(obj, (Line, Bezier)):
            continue

        rgb = obj.stroke_color

        # Fill-only paths have no stroke.
        # Laser colour normalization only applies to strokes.
        if rgb is None:
            continue

        snapped = snap_colour(rgb)

        if snapped != rgb:

            obj.stroke_color = snapped

            report.corrected += 1
    return report
