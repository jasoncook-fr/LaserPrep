"""
svg_writer.py

LaserPrep SVG exporter.

Version 0.9
"""

from pathlib import Path
from collections import defaultdict
from lxml import etree as ET

from config import (
    DISPLAY_STROKE_WIDTH_MM,
    LARGE_BED_WIDTH_MM,
    LARGE_BED_HEIGHT_MM,
)
from drawing import Line, Bezier
from vector_path import VectorPath
from project import Project

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"
NSMAP = {None: SVG_NS, "inkscape": INK_NS}

# Maximum number of line segments per SVG path.
PATH_SEGMENT_LIMIT = 5000


def _rgb_to_hex(col):
    r, g, b = col
    return f"#{r:02X}{g:02X}{b:02X}"


def _svg_root():
    return ET.Element(
        "svg",
        nsmap=NSMAP,
        width=f"{LARGE_BED_WIDTH_MM}mm",
        height=f"{LARGE_BED_HEIGHT_MM}mm",
        viewBox=f"0 0 {LARGE_BED_WIDTH_MM} {LARGE_BED_HEIGHT_MM}",
        version="1.1",
    )


def _layer(parent, name):
    return ET.SubElement(
        parent,
        "g",
        {
            f"{{{INK_NS}}}groupmode": "layer",
            f"{{{INK_NS}}}label": name,
        },
    )


def _write_line_paths(parent, lines):
    groups = defaultdict(list)

    for line in lines:
        groups[(line.stroke_color, line.stroke_width)].append(line)

    for (colour, width), objects in groups.items():

        for start in range(0, len(objects), PATH_SEGMENT_LIMIT):

            chunk = objects[start:start + PATH_SEGMENT_LIMIT]

            d = []

            for obj in chunk:
                d.append(
                    f"M {obj.start.x:.3f},{obj.start.y:.3f} "
                    f"L {obj.end.x:.3f},{obj.end.y:.3f}"
                )

            ET.SubElement(
                parent,
                "path",
                {
                    "d": " ".join(d),
                    "stroke": _rgb_to_hex(colour),
                    "stroke-width": f"{DISPLAY_STROKE_WIDTH_MM:.3f}",
                    "fill": "none",
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round",
                },
            )


def _write_imported_path(parent, path: VectorPath):
    if not path.objects:
        return

    d = []
    first = True
    stroke = None

    for obj in path.objects:
        if stroke is None:
            stroke = obj.stroke_color

        if isinstance(obj, Line):
            if first:
                d.append(f"M {obj.start.x:.3f},{obj.start.y:.3f}")
                first = False
            else:
                # Ensure continuity if needed
                d.append(f"M {obj.start.x:.3f},{obj.start.y:.3f}")
            d.append(f"L {obj.end.x:.3f},{obj.end.y:.3f}")

        elif isinstance(obj, Bezier):
            if first:
                d.append(f"M {obj.start.x:.3f},{obj.start.y:.3f}")
                first = False
            d.append(
                f"C {obj.control1.x:.3f},{obj.control1.y:.3f} "
                f"{obj.control2.x:.3f},{obj.control2.y:.3f} "
                f"{obj.end.x:.3f},{obj.end.y:.3f}"
            )

    ET.SubElement(
        parent,
        "path",
        {
            "d": " ".join(d),
            "stroke": _rgb_to_hex(stroke),
            "stroke-width": f"{DISPLAY_STROKE_WIDTH_MM:.3f}",
            "fill": "none",
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        },
    )


def write_svg(project: Project, filename: Path):

    root = _svg_root()

    for drawing in project.drawings:

        layer = _layer(root, drawing.name)

        for path in drawing.paths:
            _write_imported_path(layer, path)

    ET.ElementTree(root).write(
        str(filename),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )




