from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

from drawing import Line, Bezier
from svg_path_parser import parse_svg_path
from svg_transform import AffineTransform

PT_TO_MM = 25.4 / 72.0
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

    if _strip(node.tag) == "path":
        d = node.attrib.get("d", "")
        style = node.attrib.get("style", "")

        if d.strip() and "stroke:none" in style:
            for vp in parse_svg_path(d, stroke_color=(0, 0, 0), stroke_width=0.01):
                vp = _transform_path(vp, combined)
                vp = _scale_mm(vp)
                vp.stroke_enabled = False
                vp.fill_enabled = True
                vp.fill_color = (0, 0, 0)
                vp.is_text = True
                out.append(vp)

    for child in node:
        _walk_direct(child, combined, out)


def import_svg_paths(svg_filename):
    tree = ET.parse(svg_filename)
    root = tree.getroot()

    direct_paths = []
    _walk_direct(root, AffineTransform.identity(), direct_paths)

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
            obj.filled = True
            obj.is_text = True
            obj.group_id = group_id
            result.append(obj)

        group_id += 1

    result = direct_paths + result

    print("=" * 60)
    print("SVG TEXT IMPORT D")
    print("=" * 60)
    print(f"Glyph definitions : {len(glyphs)}")
    print(f"Direct paths      : {len(direct_paths)}")
    print(f"Total paths       : {len(result)}")

    return result


