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
        print(*args, **kwargs)


XLINK = "{http://www.w3.org/1999/xlink}href"


def _strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def _transform_path(vpath, transform):
    p = copy.deepcopy(vpath)
    p.objects = [transform.apply(o) for o in p.objects]
    return p


def _translate(vpath, dx, dy):
    return _transform_path(
        vpath,
        AffineTransform.translation(dx, dy),
    )


def _scale_mm(vpath):
    for obj in vpath:
        if isinstance(obj, Line):
            pts = [obj.start, obj.end]
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


def _walk(node, current, glyph):
    """
    Walk one Poppler glyph definition and collect its paths.

    Poppler's SVG output normally stores glyph definitions as <g
    id="glyph-..."> groups inside <defs>, rather than <symbol> elements.
    """

    local = AffineTransform.from_svg(
        node.attrib.get("transform", "")
    )
    combined = current @ local

    if _strip(node.tag) == "path":
        d = node.attrib.get("d", "")

        if d.strip():
            for vp in parse_svg_path(
                d,
                stroke_color=(0, 0, 0),
                stroke_width=0.01,
            ):
                glyph.append(
                    _transform_path(vp, combined)
                )

    for child in node:
        _walk(child, combined, glyph)


def _walk_direct(node, current, out):

    local = AffineTransform.from_svg(
        node.attrib.get("transform", "")
    )
    combined = current @ local
    tag = _strip(node.tag)

    # Never descend into glyph definitions.
    if tag == "defs":
        return

    # Glyph definitions are also skipped here. They are imported separately
    # and instantiated through their <use> elements below.
    if tag == "g" and node.attrib.get("id", "").startswith("glyph-"):
        return

    if tag == "path":

        d = node.attrib.get("d", "")
        style = node.attrib.get("style", "")

        if not d.strip():
            pass

        elif "stroke:none" not in style:
            pass

        # White filled artwork is not text.
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


def _collect_glyph_definitions(root):
    """
    Collect Poppler glyph definitions.

    Poppler uses <g id="glyph-..."> rather than <symbol>. The previous
    importer only looked for <symbol>, so documents whose text was emitted
    this way produced zero imported glyph paths.
    """

    glyphs = {}

    for node in root.iter():
        tag = _strip(node.tag)
        gid = node.attrib.get("id", "")

        if tag == "symbol":
            pass
        elif tag == "g" and gid.startswith("glyph-"):
            pass
        else:
            continue

        if not gid:
            continue

        paths = []
        _walk(
            node,
            AffineTransform.identity(),
            paths,
        )

        glyphs[gid] = paths

        _dbg(
            f"Glyph definition {gid}: "
            f"{len(paths)} paths"
        )

    return glyphs


def import_svg_paths(svg_filename):

    tree = ET.parse(svg_filename)
    root = tree.getroot()

    direct_paths = []

    _walk_direct(
        root,
        AffineTransform.identity(),
        direct_paths,
    )

    _dbg(
        f"Direct paths : {len(direct_paths)}"
    )

    glyphs = _collect_glyph_definitions(root)

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

        # A <use> can have both x/y positioning and a transform.
        dx = float(use.attrib.get("x", "0"))
        dy = float(use.attrib.get("y", "0"))

        use_transform = AffineTransform.from_svg(
            use.attrib.get("transform", "")
        )

        for vp in glyphs[gid]:

            obj = _translate(
                vp,
                dx,
                dy,
            )

            obj = _transform_path(
                obj,
                use_transform,
            )

            obj = _scale_mm(obj)

            obj.filled = True
            obj.is_text = True
            obj.group_id = group_id

            result.append(obj)

        group_id += 1

    _dbg(
        f"Direct paths : {len(direct_paths)}"
    )
    _dbg(
        f"Glyph paths  : "
        f"{len(result) - len(direct_paths)}"
    )
    _dbg(
        f"Glyph instance paths : {len(result)}"
    )

    result = direct_paths + result

    _dbg(
        f"Total imported paths : {len(result)}"
    )

    return result


def get_svg_page_size(svg_filename):
    """
    Return the SVG page size in millimetres.
    """

    tree = ET.parse(svg_filename)
    root = tree.getroot()

    viewbox = root.attrib.get("viewBox")

    if viewbox:

        x, y, w, h = map(
            float,
            viewbox.split(),
        )

        return (
            w * PT_TO_MM,
            h * PT_TO_MM,
        )

    width = root.attrib.get(
        "width",
        "",
    )

    height = root.attrib.get(
        "height",
        "",
    )

    def parse_dimension(value):

        value = value.strip()

        if value.endswith("pt"):
            return (
                float(value[:-2])
                * PT_TO_MM
            )

        if value.endswith("mm"):
            return float(value[:-2])

        return float(value)

    return (
        parse_dimension(width),
        parse_dimension(height),
    )
