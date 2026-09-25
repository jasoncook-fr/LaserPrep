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
import re

from drawing import Line, Bezier
from svg_transform import AffineTransform
from svg_path_parser import parse_svg_path
from laser_palette import snap_colour

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

def _path_intersects_page(path, page_width, page_height):
    """Return True if any path geometry lies inside the PDF page."""
    if page_width is None or page_height is None:
        return True

    for obj in path:
        if isinstance(obj, Line):
            points = [obj.start, obj.end]
        elif isinstance(obj, Bezier):
            points = [
                obj.start,
                obj.control1,
                obj.control2,
                obj.end,
            ]
        else:
            continue

        for point in points:
            if 0 <= point.x <= page_width and 0 <= point.y <= page_height:
                return True

    return False

def import_svg_geometry(svg_filename, page_width=None, page_height=None):

    tree = ET.parse(svg_filename)
    root = tree.getroot()

    result = []

    drawing_id = 0

    def _artwork_paths(node, inside_non_artwork=False):

        tag = _strip(node.tag)

        # Definitions and clipping geometry are not visible artwork.
        # In particular, MuPDF may place font glyph definitions inside
        # <defs>. Those paths must never be imported as drawing geometry.
        inside_non_artwork = (
            inside_non_artwork
            or tag in ("defs", "clipPath")
        )

        if tag == "path" and not inside_non_artwork:
            yield node

        for child in node:
            yield from _artwork_paths(
                child,
                inside_non_artwork,
            )

    for node in _artwork_paths(root):

        d = node.attrib.get("d", "").strip()

        if not d:
            continue

        # Skip completely invisible SVG paths.
        stroke_attr = node.attrib.get("stroke", "").strip().lower()
        fill_attr = node.attrib.get("fill", "").strip().lower()

        stroke_opacity = node.attrib.get("stroke-opacity", "1").strip()
        fill_opacity = node.attrib.get("fill-opacity", "1").strip()

        if (
            (stroke_attr == "none" or stroke_opacity == "0")
            and
            (fill_attr == "none" or fill_opacity == "0")
        ):
            continue

        drawing_id += 1

        stroke = _parse_colour(node.attrib.get("stroke"))

        # Black in the source artwork is engraving artwork. MuPDF may omit
        # the fill attribute because black is SVG's default fill.
        fill_attr_raw = node.attrib.get("fill")

        if fill_attr_raw is None and stroke is None:
            fill = (0, 0, 0)
        else:
            fill = _parse_colour(fill_attr_raw)

        # Normalize near-official fill colours before deciding whether
        # the fill is meaningful.
        #
        # This is important because MuPDF may export black PDF artwork
        # as a slightly tinted colour such as #080606 rather than #000000.
        # LaserPrep's colour palette already defines how near-colours
        # should be snapped.
        if fill is not None:
            fill = snap_colour(fill)

        # LaserPrep uses black fills for engraving and white fills as
        # subtraction/masking geometry (for example the owl's eyes and beak).
        # Ignore other coloured PDF fills such as the Archicad watermark.
        if fill not in ((0, 0, 0), (255, 255, 255), None):
            continue

        width = _parse_width(
            node.attrib.get("stroke-width")
        )

        transform_text = node.attrib.get("transform", "")
        transform = AffineTransform.from_svg(transform_text)

        # MuPDF's stroke-width is expressed before the SVG transform.
        # Convert it to the effective width after the transform.
        stroke_scale = 1.0

        matrix_match = re.search(
            r"matrix\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,"
            r"\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)",
            transform_text,
        )

        if matrix_match:

            ma, mb, mc, md = (
                float(value)
                for value in matrix_match.groups()
            )

            sx = (ma * ma + mb * mb) ** 0.5
            sy = (mc * mc + md * md) ** 0.5

            if sx and sy:
                stroke_scale = (sx + sy) / 2.0
            elif sx:
                stroke_scale = sx
            elif sy:
                stroke_scale = sy

        paths = parse_svg_path(
            d,
            stroke_color=stroke,
            stroke_width=width,
            transform=transform_text,
        )

        for path in paths:

            path = _transform_path(path, transform)
            path = _scale_mm(path)

            if not _path_intersects_page(
                path,
                page_width,
                page_height,
            ):
                continue

            path.stroke_color = stroke
            path.fill_color = fill

            path.stroke_enabled = stroke is not None
            path.fill_enabled = fill is not None

            # Store the effective source stroke width in millimetres.
            path.stroke_width = width * stroke_scale * PT_TO_MM

            path.source_drawing = drawing_id

            result.append(path)

    return result
