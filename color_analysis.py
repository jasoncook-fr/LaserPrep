"""
color_analysis.py

Colour analysis.

Version 0.7.1
"""

from drawing import Drawing, Line, Bezier
from laser_palette import (
    OFFICIAL_LASER_COLORS,
    classify_colour,
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

        # Near official colours
        self.near = {}

        # Unsupported colours
        self.unsupported = {}

# ============================================================
# ANALYSIS
# ============================================================

def analyse_colors(drawing: Drawing) -> ColorReport:

    report = ColorReport()

    for obj in drawing.objects:

        if not isinstance(obj, (Line, Bezier)):
            continue

        # Convert float RGB (0–1) to integer RGB (0–255)
        rgb = obj.stroke_color

        # Filled paths have no stroke colour.
        # They will be analysed separately later.
        if rgb is None:
            continue

        status, name, distance = classify_colour(rgb)

        if status == "OFFICIAL":

            report.official[name] += 1

        elif status == "NEAR":

            if rgb not in report.near:

                report.near[rgb] = {
                    "target": name,
                    "count": 0,
                    "distance": distance,
                }

            report.near[rgb]["count"] += 1

        else:

            report.unsupported[rgb] = (
                report.unsupported.get(rgb, 0) + 1
            )

    return report
