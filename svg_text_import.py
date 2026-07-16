from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

DEBUG = False

from drawing import Line, Bezier
from svg_path_parser import parse_svg_path
from svg_transform import AffineTransform

PT_TO_MM = 25.4 / 72.0


def _dbg(*args, **kwargs):
    if DEBUG:
        _dbg(*args, **kwargs)
XLINK = "{http://www.w3.org/1999/xlink}href"


def _strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def _transform_path(vpath, transform):
    p = copy.deepcopy(vpath)
    p.objects = [transform.apply(o) for o in p.objects]
    return p


def _translate(vpath, dx, dy):
    return _transform_path(vpath, AffineTransform.translation(dx, dy))


def _scale_mm(vpath):
    for obj in vpath:
        if isinstance(obj, Line):
            pts = [obj.start, obj.end]
        elif isinstance(obj, Bezier):
            pts = [obj.start, obj.control1, obj.control2, obj.end]
        else:
            continue

        for pt in pts:
            pt.x *= PT_TO_MM
            pt.y *= PT_TO_MM

        obj.stroke_width *= PT_TO_MM

    return vpath


def _walk(node, current, glyph):
    local = AffineTransform.from_svg(node.attrib.get("transform", ""))
    combined = current @ local

    if _strip(node.tag) == "path":
        d = node.attrib.get("d", "")
        if d.strip():
            for vp in parse_svg_path(d, stroke_color=(0, 0, 0), stroke_width=0.01):
                glyph.append(_transform_path(vp, combined))

    for child in node:
        _walk(child, combined, glyph)

def _walk_direct(node, current, out):

    local = AffineTransform.from_svg(node.attrib.get("transform", ""))
    combined = current @ local
    tag = _strip(node.tag)

    #
    # Never descend into glyph definitions.
    #
    if tag in ("defs", "symbol"):
        return

    if tag == "path":
    #if _strip(node.tag) == "path":

        d = node.attrib.get("d", "")
        style = node.attrib.get("style", "")

        if not d.strip():
            pass

        elif "stroke:none" not in style:
            pass

        #
        # IMPORTANT:
        #
        # Some CAD / Archicad PDFs contain filled vector artwork
        # (typically white) that Poppler exports as:
        #
        #     stroke:none;
        #     fill:rgb(100%,100%,100%);
        #
        # Those are NOT text glyphs.
        #
        # Only import black filled paths as direct text.
        #
        elif "fill:rgb(100%" in style:
            pass

        else:
            for vp in parse_svg_path(
                d,
                stroke_color=(0, 0, 0),
                stroke_width=0.01,
            ):

                vp = _transform_path(vp, combined)
                vp = _scale_mm(vp)

                vp.stroke_enabled = False
                vp.fill_enabled = True
                vp.fill_color = (0, 0, 0)
                vp.is_text = True

                if (
                    "stroke:none" in style
                    and "fill:" in style
                ):
                    vp.is_direct_text = True

                _dbg()
                _dbg("DIRECT PATH")
                _dbg(f"Style : {style}")
                _dbg(f"Bounds: {vp.bounds}")
                _dbg(f"Closed: {vp.closed}")
                out.append(vp)

    for child in node:
        _walk_direct(child, combined, out)


def import_svg_paths(svg_filename):
    tree = ET.parse(svg_filename)
    root = tree.getroot()

    direct_paths = []
    _walk_direct(root, AffineTransform.identity(), direct_paths)
    _dbg(f"Direct paths : {len(direct_paths)}")

    glyphs = {}

    for symbol in root.iter():
        if _strip(symbol.tag) != "symbol":
            continue

        gid = symbol.attrib.get("id")
        if not gid:
            continue

        paths = []
        _walk(symbol, AffineTransform.identity(), paths)
        glyphs[gid] = paths
        _dbg(f"Glyph definitions : {len(glyphs)}")

    result = []
    group_id = 1
    for use in root.iter():
        if _strip(use.tag) != "use":
            continue

        href = use.attrib.get(XLINK)
        if not href:
            continue

        gid = href.lstrip("#")
        if gid not in glyphs:
            continue

        dx = float(use.attrib.get("x", "0"))
        dy = float(use.attrib.get("y", "0"))
        for vp in glyphs[gid]:
            obj = _scale_mm(_translate(vp, dx, dy))
            first = next(iter(obj))
            obj.filled = True
            obj.is_text = True
            obj.group_id = group_id
            result.append(obj)

        group_id += 1

    _dbg(f"Direct paths : {len(direct_paths)}")
    _dbg(f"Glyph paths  : {len(result) - len(direct_paths)}")
    _dbg(f"Glyph instance paths : {len(result)}")
    result = direct_paths + result
    _dbg(f"Total imported paths : {len(result)}")

    return result

def get_svg_page_size(svg_filename):
    """
    Return the SVG page size in millimetres.

    Returns
    -------
    (width_mm, height_mm)
    """

    tree = ET.parse(svg_filename)
    root = tree.getroot()

    #
    # Prefer the SVG viewBox.
    #
    viewbox = root.attrib.get("viewBox")

    if viewbox:

        x, y, w, h = map(float, viewbox.split())

        return (
            w * PT_TO_MM,
            h * PT_TO_MM,
        )

    #
    # Fallback to width / height attributes.
    #
    width = root.attrib.get("width", "")
    height = root.attrib.get("height", "")

    def parse_dimension(value):

        value = value.strip()

        if value.endswith("pt"):
            return float(value[:-2]) * PT_TO_MM

        if value.endswith("mm"):
            return float(value[:-2])

        return float(value)

    return (
        parse_dimension(width),
        parse_dimension(height),
    )




