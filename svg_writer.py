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


def _subpath_groups(path):
    """Return contiguous segment groups without changing segment geometry."""
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
    return groups


def _make_path_like(path, segments, *, closed=False):
    """Build a Path carrying the source path's style and exporter metadata."""
    from drawing import Path
    result = Path(
        segments=list(segments), closed=closed,
        stroke_color=path.stroke_color, fill_color=path.fill_color,
        stroke_width=path.stroke_width, stroke_enabled=path.stroke_enabled,
        fill_enabled=path.fill_enabled, is_text=path.is_text,
        import_order=path.import_order,
    )
    for attribute in ("preserve_stroke_width", "is_black_engraving"):
        if hasattr(path, attribute):
            setattr(result, attribute, getattr(path, attribute))
    return result


def _group_extent(group):
    points = []
    for segment in group:
        points.extend((segment.start, segment.end))
        if isinstance(segment, Bezier):
            points.extend((segment.control1, segment.control2))
    if not points:
        return 0.0
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))

def _reorder_disconnected_subpaths(path):
    """Reorder disconnected open subpaths within one Path object.

    Unlike splitting a path into separate Path objects, this keeps the number
    of SVG path elements stable. Segment direction and geometry are preserved.
    Filled paths, text, closed paths, and special black engraving paths are
    left untouched because their closure/fill semantics may be significant.
    """
    if (
        path.is_empty
        or path.fill_color is not None
        or getattr(path, "is_text", False)
        or getattr(path, "closed", False)
        or getattr(path, "is_black_engraving", False)
    ):
        return path

    groups = _subpath_groups(path)

    if len(groups) <= 1:
        return path

    # Greedily reorder the disconnected subpaths while never reversing any
    # segment or changing the geometry within a subpath.
    remaining = list(groups)
    ordered = []
    current_point = None

    while remaining:
        if current_point is None:
            index = 0  # Keep the first subpath stable as the starting point.
        else:
            def distance_squared(group):
                start = group[0].start
                dx = start.x - current_point.x
                dy = start.y - current_point.y
                return dx * dx + dy * dy

            index = min(
                range(len(remaining)),
                key=lambda i: distance_squared(remaining[i]),
            )

        chosen = remaining.pop(index)
        ordered.append(chosen)
        current_point = chosen[-1].end

    return _make_path_like(
        path, [segment for group in ordered for segment in group], closed=False
    )


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
                segments = list(path)

                if not segments:
                    return float("inf")

                start = segments[0].start
                dx = start.x - current_point.x
                dy = start.y - current_point.y
                return dx * dx + dy * dy

            index = min(
                range(len(remaining)),
                key=lambda i: distance_squared(remaining[i]),
            )

        chosen = remaining.pop(index)
        ordered.append(chosen)

        chosen_segments = list(chosen)
        if chosen_segments:
            current_point = chosen_segments[-1].end

    return ordered


def _write_imported_path(parent, path):
    global PATH_INDEX
    if path.is_empty:
        return
    PATH_INDEX += 1

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
    """Order engraving first, blue cuts next, and the largest geometrically
    closed blue contour last. All other closed contours remain in the output.
    """
    BLUE = (0, 0, 255)
    engraving = []
    cutting = []
    closed_cutting = []
    border_candidates = []

    for path in paths:
        if (
            path.stroke_color != BLUE
            or path.fill_color is not None
            or getattr(path, "is_text", False)
        ):
            engraving.append(path)
            continue

        # Explicitly closed paths stay intact and remain eligible for the
        # outer-border selection, but are not discarded while selecting it.
        if getattr(path, "closed", False):
            segments = list(path)
            if segments:
                closed_cutting.append(path)
                border_candidates.append(
                    (_group_extent(segments), "path", path, None, path)
                )
            continue

        # Keep every disconnected subpath. Only one largest closed contour
        # will later be extracted as the final border.
        groups = _subpath_groups(path)
        if not groups:
            continue

        for group in groups:
            geometrically_closed = (
                len(group) > 2 and _same_point(group[0].start, group[-1].end)
            )
            if geometrically_closed:
                border_candidates.append(
                    (_group_extent(group), "group", path, group, None)
                )

        # Rebuild this source path with all of its groups intact for now.
        combined = _make_path_like(
            path,
            [segment for group in groups for segment in group],
            closed=False,
        )
        setattr(combined, "_laserprep_source_path", path)
        cutting.append(combined)

    outer_border = None
    if border_candidates:
        _, kind, source_path, border_group, whole_path = max(
            border_candidates, key=lambda item: item[0]
        )
        if kind == "path":
            outer_border = whole_path
            closed_cutting = [p for p in closed_cutting if p is not whole_path]
        else:
            outer_border = _make_path_like(
                source_path, border_group, closed=False
            )
            # Remove only the selected border group from the remaining path.
            for index, original in enumerate(paths):
                if original is source_path:
                    groups = _subpath_groups(original)
                    remaining_groups = [
                        group for group in groups if group is not border_group
                    ]
                    cutting = [
                        p for p in cutting
                        if not (
                            getattr(p, "_laserprep_source_path", None)
                            is source_path
                        )
                    ]
                    if remaining_groups:
                        remainder = _make_path_like(
                            source_path,
                            [segment for group in remaining_groups for segment in group],
                            closed=False,
                        )
                        setattr(remainder, "_laserprep_source_path", source_path)
                        cutting.append(remainder)
                    break

    # Mark source paths so the selected contour can be removed cleanly without
    # dropping any other subpaths from the same original path.
    # (Rebuilds above preserve all non-border geometry.)
    if OPTIMIZE_CUT_ORDER:
        engraving = [_reorder_disconnected_subpaths(path) for path in engraving]
        engraving = _nearest_neighbour_order(engraving)
        cutting = [_reorder_disconnected_subpaths(path) for path in cutting]
        cutting = _nearest_neighbour_order(cutting)
        closed_cutting = _nearest_neighbour_order(closed_cutting)

    return engraving + cutting + closed_cutting + ([outer_border] if outer_border else [])


def write_svg(project: Project, filename: Path):
    global PATH_INDEX
    PATH_INDEX = 0
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
