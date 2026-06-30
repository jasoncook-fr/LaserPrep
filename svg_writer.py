"""
svg_writer.py

LaserPrep SVG exporter.

Version 0.3
"""

from pathlib import Path
from lxml import etree as ET
from config import DISPLAY_STROKE_WIDTH_MM
from drawing import Line, Bezier
from project import Project
from config import LARGE_BED_WIDTH_MM, LARGE_BED_HEIGHT_MM
SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"

NSMAP = {None: SVG_NS, "inkscape": INK_NS}


def _rgb_to_hex(col):
    r = max(0, min(255, round(col[0] * 255)))
    g = max(0, min(255, round(col[1] * 255)))
    b = max(0, min(255, round(col[2] * 255)))
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


def _line(parent, obj, duplicate=False):
    ET.SubElement(
        parent,
        "line",
        {
            "x1": f"{obj.start.x:.3f}",
            "y1": f"{obj.start.y:.3f}",
            "x2": f"{obj.end.x:.3f}",
            "y2": f"{obj.end.y:.3f}",
            "stroke": "#FF0000" if duplicate else _rgb_to_hex(obj.stroke_color),
            "stroke-width": (
                "0.40"
                if duplicate
                else f"{DISPLAY_STROKE_WIDTH_MM:.3f}"
            ),
            "fill": "none",
        },
    )


def _bezier(parent, obj):
    d = (
        f"M {obj.start.x:.3f},{obj.start.y:.3f} "
        f"C {obj.control1.x:.3f},{obj.control1.y:.3f} "
        f"{obj.control2.x:.3f},{obj.control2.y:.3f} "
        f"{obj.end.x:.3f},{obj.end.y:.3f}"
    )

    ET.SubElement(
        parent,
        "path",
        {
            "d": d,
            "stroke": _rgb_to_hex(obj.stroke_color),
            "stroke-width": f"{obj.stroke_width:.3f}",
            "fill": "none",
        },
    )


def write_svg(project: Project, filename: Path):
    """
    Export a Project as an Inkscape-compatible SVG.
    Each Drawing becomes one Inkscape layer.
    """

    root = _svg_root()

    for drawing in project.drawings:
        layer = _layer(root, drawing.name)

        for obj in drawing.objects:

            if isinstance(obj, Line):

                _line(
                    layer,
                    obj,
                )

            elif isinstance(obj, Bezier):

                _bezier(layer, obj)

            elif isinstance(obj, Bezier):
                _bezier(layer, obj)

    tree = ET.ElementTree(root)
    tree.write(
        str(filename),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )
