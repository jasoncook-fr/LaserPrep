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
    OPTIMIZE_CUT_ORDER,
)
from drawing import Line, Bezier
from project import Project

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"
SODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
NSMAP = {None: SVG_NS, "inkscape": INK_NS, "sodipodi": SODI_NS}

PATH_SEGMENT_LIMIT = 5000
PATH_INDEX = 0

def _rgb_to_hex(col):
    r, g, b = col
    return f"#{r:02X}{g:02X}{b:02X}"


def _svg_root():
    root = ET.Element(
        "svg",
        nsmap=NSMAP,
        width=f"{LARGE_BED_WIDTH_MM}mm",
        height=f"{LARGE_BED_HEIGHT_MM}mm",
        viewBox=f"0 0 {LARGE_BED_WIDTH_MM} {LARGE_BED_HEIGHT_MM}",
        version="1.1",
    )

    # Inkscape document display defaults: transparent page with checkerboard.
    ET.SubElement(
        root,
        f"{{{SODI_NS}}}namedview",
        {
            "id": "namedview1",
            "pagecolor": "#ffffff",
            "bordercolor": "#666666",
            "borderopacity": "1.0",
            f"{{{INK_NS}}}pageopacity": "0.0",
            f"{{{INK_NS}}}pageshadow": "2",
            f"{{{INK_NS}}}pagecheckerboard": "1",
            f"{{{INK_NS}}}deskcolor": "#d1d1d1",
        },
    )

    return root


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

            if transform:
                print(transform)
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


def _split_disconnected_subpaths(path):
    """Split an unfilled stroke at discontinuities without changing geometry."""
    if (
        path.is_empty
        or path.fill_color is not None
        or getattr(path, "is_text", False)
        or getattr(path, "closed", False)
    ):
        return [path]

    groups = []
    current = []
    previous_end = None

    for segment in path:
        if current and not _same_point(segment.start, previous_end):
            groups.append(current)
            current = []
        current.append(segment)
        previous_end = segment.end

    if current:
        groups.append(current)

    if len(groups) <= 1:
        return [path]

    from drawing import Path

    result = []
    for group in groups:
        is_closed = (
            getattr(path, "closed", False)
            and _same_point(group[0].start, group[-1].end)
        )

        result.append(Path(
            segments=list(group),
            closed=is_closed,
            stroke_color=path.stroke_color,
            fill_color=path.fill_color,
            stroke_width=path.stroke_width,
            stroke_enabled=path.stroke_enabled,
            fill_enabled=path.fill_enabled,
            is_text=path.is_text,
            import_order=path.import_order,
        ))

    return result


def _nearest_neighbour_order(paths):
    """Reorder whole strokes by travel distance; never reverse their direction."""
    remaining = list(paths)
    ordered = []
    current_point = None

    while remaining:
        if current_point is None:
            # Keep the first stroke stable.
            index = 0
        else:
            def distance_squared(path):
                start = path.segments[0].start
                dx = start.x - current_point.x
                dy = start.y - current_point.y
                return dx * dx + dy * dy

            index = min(
                range(len(remaining)),
                key=lambda i: distance_squared(remaining[i]),
            )

        chosen = remaining.pop(index)
        ordered.append(chosen)
        current_point = chosen.segments[-1].end

    return ordered


def _write_imported_path(parent, path):
    '''
    global PATH_INDEX
    PATH_INDEX += 1
    if PATH_INDEX == 16:
        print("\n" + "=" * 60)
        print("PATH 16")
        print("=" * 60)
        print(f"closed = {path.closed}")
        print(f"objects = {len(path.objects)}")

        for i, obj in enumerate(path.objects):
            print(i, type(obj).__name__, obj.start, "->", obj.end)
    '''
    if path.is_empty:
        return

    d = []
    stroke = path.stroke_color
    fill = path.fill_color
    previous_end = None

    is_black_engraving = getattr(
        path,
        "is_black_engraving",
        False,
    )

    for obj in path:

        if previous_end is None or not _same_point(obj.start, previous_end):
            if is_black_engraving and previous_end is not None:
                d.append("Z")

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

    if getattr(path, "closed", False):
        #print(f"Closing path {PATH_INDEX}")
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

        if getattr(path, "preserve_stroke_width", False):
            attrs["stroke-width"] = f"{path.stroke_width:.3f}"
        else:
            attrs["stroke-width"] = f"{DISPLAY_STROKE_WIDTH_MM:.3f}"
        attrs["stroke-linecap"] = "round"
        attrs["stroke-linejoin"] = "round"
    else:
        attrs["stroke"] = "none"

    if fill is not None:
        attrs["fill"] = _rgb_to_hex(fill)
        attrs["fill-rule"] = "evenodd"
    else:
        attrs["fill"] = "none"

    ET.SubElement(
        parent,
        "path",
        {
            **attrs,
            "id": f"path{PATH_INDEX}",
        },
    )


def _order_paths_for_laser(paths):
    """
    Order engraving first, then interior cuts, then closed cuts, with the
    existing largest explicitly closed blue contour last.
    """
    BLUE = (0, 0, 255)
    engraving = []
    cutting = []
    closed_cutting = []

    for path in paths:
        if path.stroke_color != BLUE:
            engraving.append(path)
            continue

        # Keep filled artwork/text intact.
        if path.fill_color is not None or getattr(path, "is_text", False):
            engraving.append(path)
            continue

        pieces = (
            _split_disconnected_subpaths(path)
            if OPTIMIZE_CUT_ORDER
            else [path]
        )

        for piece in pieces:
            if getattr(piece, "closed", False):
                closed_cutting.append(piece)
            else:
                cutting.append(piece)

    # Preserve the existing explicit-closed-path outer-border rule.
    def path_extent(path):
        points = []
        for obj in path:
            if isinstance(obj, Line):
                points.extend((obj.start, obj.end))
            elif isinstance(obj, Bezier):
                points.extend((
                    obj.start, obj.control1, obj.control2, obj.end
                ))

        if not points:
            return 0.0

        xs = [point.x for point in points]
        ys = [point.y for point in points]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    outer_border = None
    if closed_cutting:
        outer_border = max(closed_cutting, key=path_extent)
        closed_cutting.remove(outer_border)

    if OPTIMIZE_CUT_ORDER:
        cutting = _nearest_neighbour_order(cutting)
        closed_cutting = _nearest_neighbour_order(closed_cutting)

    return (
        engraving
        + cutting
        + closed_cutting
        + ([outer_border] if outer_border is not None else [])
    )


def write_svg(project: Project, filename: Path):

    root = _svg_root()

    for drawing in project.drawings:
        layer = _layer(root, drawing.name)

        ordered_paths = _order_paths_for_laser(drawing.paths)

        for path in ordered_paths:
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










def write_bad_colors_svg(drawing, filename, unsupported_colors):
    """
    Export only geometry using unsupported stroke colours.

    No normalization or cleanup is applied.
    """

    root = _svg_root()
    layer = _layer(root, drawing.name)

    for path in drawing.paths:
        stroke = getattr(path, "stroke_color", None)

        if stroke not in unsupported_colors:
            continue

        _write_imported_path(layer, path)

        # Make unsupported colours visually obvious in the diagnostic.
        element = layer[-1]
        element.set("stroke-width", "2.0")

    ET.ElementTree(root).write(
        str(filename),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )
