"""
color_analysis.py

Colour analysis.

Version 0.7.1
"""

from drawing import Drawing, Line, Bezier
from laser_palette import (
    OFFICIAL_LASER_COLORS,
    colour_name,
)


# ============================================================
# REPORT
# ============================================================

class ColorReport:

    def __init__(self):

        # Count of official colours
        self.official = {
            name: 0
            for name in OFFICIAL_LASER_COLORS
        }

        # Unknown colours
        self.unknown = {}


# ============================================================
# ANALYSIS
# ============================================================

def analyse_colors(drawing: Drawing) -> ColorReport:

    report = ColorReport()

    for obj in drawing.objects:

        if not isinstance(obj, (Line, Bezier)):
            continue

        # Convert float RGB (0–1) to integer RGB (0–255)
        rgb = (
            round(obj.stroke_color[0] * 255),
            round(obj.stroke_color[1] * 255),
            round(obj.stroke_color[2] * 255),
        )

        name = colour_name(rgb)

        if name is not None:

            report.official[name] += 1

        else:

            report.unknown[rgb] = (
                report.unknown.get(rgb, 0) + 1
            )

    return report
