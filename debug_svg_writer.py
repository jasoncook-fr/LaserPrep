"""
debug_svg_writer.py

LaserPrep
Debug SVG Writer

Version 1.0

Writes imported VectorPaths to a standalone SVG for diagnostics.

This module is intentionally simple.
It performs no cleanup, no normalization, no transforms.
"""

from __future__ import annotations

from xml.sax.saxutils import escape


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _rgb(rgb):

    if rgb is None:
        return "none"

    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _point(p):

    return f"{p.x:.6f},{p.y:.6f}"


# ------------------------------------------------------------
# Path conversion
# ------------------------------------------------------------
def _same_point(a, b, eps=1e-6):
    return (
        abs(a.x - b.x) < eps and
        abs(a.y - b.y) < eps
    )


def _vector_path_to_svg(path):

    commands = []

    previous_end = None

    for obj in path:

        if previous_end is None or not _same_point(obj.start, previous_end):

            commands.append(
                f"M {_point(obj.start)}"
            )

        if obj.__class__.__name__ == "Line":

            commands.append(
                f"L {_point(obj.end)}"
            )

        else:

            commands.append(
                "C "
                f"{_point(obj.control1)} "
                f"{_point(obj.control2)} "
                f"{_point(obj.end)}"
            )

        previous_end = obj.end

    commands.append("Z")

    return " ".join(commands)

# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def write_imported_paths(paths, filename):

    xmin = float("inf")
    ymin = float("inf")
    xmax = float("-inf")
    ymax = float("-inf")

    for path in paths:

        for obj in path:

            points = []

            if obj.__class__.__name__ == "Line":

                points = [
                    obj.start,
                    obj.end,
                ]

            else:

                points = [
                    obj.start,
                    obj.control1,
                    obj.control2,
                    obj.end,
                ]

            for p in points:

                xmin = min(xmin, p.x)
                ymin = min(ymin, p.y)
                xmax = max(xmax, p.x)
                ymax = max(ymax, p.y)

    if xmin == float("inf"):

        xmin = 0
        ymin = 0
        xmax = 100
        ymax = 100

    margin = 10

    xmin -= margin
    ymin -= margin
    xmax += margin
    ymax += margin

    width = xmax - xmin
    height = ymax - ymin

    with open(filename, "w", encoding="utf-8") as fp:

        fp.write('<?xml version="1.0" encoding="UTF-8"?>\n')

        fp.write(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width:.3f}mm" '
            f'height="{height:.3f}mm" '
            f'viewBox="{xmin:.3f} {ymin:.3f} {width:.3f} {height:.3f}">\n'
        )

        fp.write("<g>\n")

        for path in paths:

            d = _vector_path_to_svg(path)

            stroke = _rgb(path.stroke_color)

            fill = "black" if getattr(path, "filled", False) else "none"

            width = getattr(path, "stroke_width", 0.01)

            fp.write(
                f'<path d="{escape(d)}" '
                f'stroke="{stroke}" '
                f'fill="{fill}" '
                f'stroke-width="{width:.4f}" '
                f'vector-effect="non-scaling-stroke"/>\n'
            )

        fp.write("</g>\n")
        fp.write("</svg>\n")

    print(f"Debug SVG written: {filename}")
