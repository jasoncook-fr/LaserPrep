"""
svg_writer_v2.py

LaserPrep SVG exporter.
Version 1.0

Adds support for filled VectorPaths (used for imported text).
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
from project import Project

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"
NSMAP = {None: SVG_NS, "inkscape": INK_NS}

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


def _same_point(a, b, eps=1e-6):
    return abs(a.x - b.x) < eps and abs(a.y - b.y) < eps


def _write_imported_path(parent, path):
    print("WRITE:", getattr(path, "is_text", False))
    if path.is_empty:
        return

    d = []
    stroke = path.stroke_color
    fill = path.fill_color
    previous_end = None

    for obj in path:

        if previous_end is None or not _same_point(obj.start, previous_end):
            d.append(f"M {obj.start.x:.3f},{obj.start.y:.3f}")

        if isinstance(obj, Line):
            d.append(f"L {obj.end.x:.3f},{obj.end.y:.3f}")
            previous_end = obj.end

        elif isinstance(obj, Bezier):
            d.append(
                f"C "
                f"{obj.control1.x:.3f},{obj.control1.y:.3f} "
                f"{obj.control2.x:.3f},{obj.control2.y:.3f} "
                f"{obj.end.x:.3f},{obj.end.y:.3f}"
            )
            previous_end = obj.end

    d.append("Z")

    attrs = {"d": " ".join(d)}

    if getattr(path, "is_text", False):
        attrs["fill"] = "#000000"
        attrs["fill-rule"] = "evenodd"
        attrs["stroke"] = "none"
        ET.SubElement(parent, "path", attrs)
        return

    if path.stroke_enabled and stroke is not None:
        attrs["stroke"] = _rgb_to_hex(stroke)
        attrs["stroke-width"] = f"{DISPLAY_STROKE_WIDTH_MM:.3f}"
        attrs["stroke-linecap"] = "round"
        attrs["stroke-linejoin"] = "round"
    else:
        attrs["stroke"] = "none"

    if path.fill_enabled and fill is not None:
        attrs["fill"] = _rgb_to_hex(fill)
        attrs["fill-rule"] = "evenodd"
    else:
        attrs["fill"] = "none"

    ET.SubElement(parent, "path", attrs)


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

# ============================================================
# DEBUG EXPORT
# ============================================================

def write_debug_svg(drawing, filename: Path):
    """
    Export a single Drawing exactly as it currently exists.

    Used by the Diagnostics system.

    No cleanup.
    No colour normalization.
    No modifications.
    """

    root = _svg_root()

    layer = _layer(root, drawing.name)

    for path in drawing.paths:
        _write_imported_path(layer, path)

    ET.ElementTree(root).write(
        str(filename),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )




