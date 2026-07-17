"""
svg_geometry_import.py

LaserPrep Geometry Import
Version 1.2

Imports geometry from MuPDF-generated SVG.

Text is ignored.

One SVG <path> becomes one or more VectorPaths.
"""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

from drawing import Line, Bezier
from svg_transform import AffineTransform
from svg_path_parser import parse_svg_path

SVG_NS = "{http://www.w3.org/2000/svg}"

PT_TO_MM = 25.4 / 72.0


def _strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def _parse_colour(value):

    if not value:
        return None

    value = value.strip()

    if value == "none":
        return None

    if value.startswith("#"):

        value = value[1:]

        if len(value) == 6:
            return (
                int(value[0:2], 16),
                int(value[2:4], 16),
                int(value[4:6], 16),
            )

    return (0, 0, 0)


def _parse_width(value):

    if not value:
        return 0.01

    value = value.replace("pt", "")
    value = value.replace("px", "")

    try:
        return float(value)
    except ValueError:
        return 0.01


def _transform_path(vpath, transform):

    path = copy.deepcopy(vpath)
    path.objects = [transform.apply(obj) for obj in path.objects]
    return path


def _scale_mm(vpath):

    for obj in vpath:

        if isinstance(obj, Line):
            pts = [
                obj.start,
                obj.end,
            ]

        elif isinstance(obj, Bezier):
            pts = [
                obj.start,
                obj.control1,
                obj.control2,
                obj.end,
            ]

        else:
            continue

        for pt in pts:
            pt.x *= PT_TO_MM
            pt.y *= PT_TO_MM

        obj.stroke_width *= PT_TO_MM

    return vpath


def import_svg_geometry(svg_filename):

    tree = ET.parse(svg_filename)
    root = tree.getroot()

    result = []

    drawing_id = 0

    for node in root.iter():

        if _strip(node.tag) != "path":
            continue

        d = node.attrib.get("d", "").strip()

        if not d:
            continue

        # Skip completely invisible SVG paths.
        stroke_attr = node.attrib.get("stroke", "").strip().lower()
        fill_attr = node.attrib.get("fill", "").strip().lower()

        stroke_opacity = node.attrib.get("stroke-opacity", "1").strip()
        fill_opacity = node.attrib.get("fill-opacity", "1").strip()

        if (
            (stroke_attr in ("", "none") or stroke_opacity == "0")
            and
            (fill_attr in ("", "none") or fill_opacity == "0")
        ):
            continue

        drawing_id += 1

        stroke = _parse_colour(node.attrib.get("stroke"))

        # Geometry import intentionally ignores PDF fills.
        # Text is imported separately through the Poppler pipeline.
        fill = None

        width = _parse_width(
            node.attrib.get("stroke-width")
        )

        transform_text = node.attrib.get("transform", "")
        transform = AffineTransform.from_svg(transform_text)

        paths = parse_svg_path(
            d,
            stroke_color=stroke,
            stroke_width=width,
            transform=transform_text,
        )

        for path in paths:

            path = _transform_path(path, transform)
            path = _scale_mm(path)

            path.stroke_color = stroke
            path.fill_color = fill

            path.stroke_enabled = stroke is not None
            path.fill_enabled = False

            # Store stroke width in millimetres.
            path.stroke_width = width * PT_TO_MM

            path.source_drawing = drawing_id

            result.append(path)

    return result
