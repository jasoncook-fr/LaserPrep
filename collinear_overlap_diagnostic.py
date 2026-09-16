"""
collinear_overlap_diagnostic.py

Diagnostic-only analysis of redundant straight-line geometry.

This module is deliberately separate from geometry_cleanup.py:
it does not modify Drawing.objects and it does not participate in
production cleanup yet.

It looks for same-colour Line objects that:
- are almost exactly collinear,
- lie on essentially the same physical path,
- overlap for most of the shorter segment.

The implementation uses angle/line-offset buckets and interval sorting
instead of an O(n²) all-pairs comparison.
"""

from __future__ import annotations

import math
from collections import defaultdict

from drawing import Drawing, Line
from config import (
    COLLINEAR_ANGLE_TOLERANCE_DEG,
    COLLINEAR_SEPARATION_TOLERANCE_MM,
    COLLINEAR_MIN_SEGMENT_LENGTH_MM,
    COLLINEAR_MIN_OVERLAP_RATIO,
)

# Bucket widths are deliberately tied to the configured tolerances.
ANGLE_BIN_DEG = COLLINEAR_ANGLE_TOLERANCE_DEG
OFFSET_BIN_MM = COLLINEAR_SEPARATION_TOLERANCE_MM

ANGLE_TOL_DEG = COLLINEAR_ANGLE_TOLERANCE_DEG
LINE_OFFSET_TOL_MM = COLLINEAR_SEPARATION_TOLERANCE_MM
MIN_SEGMENT_LENGTH_MM = COLLINEAR_MIN_SEGMENT_LENGTH_MM
MIN_OVERLAP_RATIO = COLLINEAR_MIN_OVERLAP_RATIO


def _line_length(line: Line) -> float:
    return math.hypot(
        line.end.x - line.start.x,
        line.end.y - line.start.y,
    )


def _segment_data(line: Line):
    length = _line_length(line)
    if length < MIN_SEGMENT_LENGTH_MM:
        return None

    theta = math.atan2(
        line.end.y - line.start.y,
        line.end.x - line.start.x,
    ) % math.pi

    ux = math.cos(theta)
    uy = math.sin(theta)
    nx = -uy
    ny = ux

    c = nx * line.start.x + ny * line.start.y
    t0 = ux * line.start.x + uy * line.start.y
    t1 = ux * line.end.x + uy * line.end.y

    return {
        "line": line,
        "length": length,
        "theta": theta,
        "c": c,
        "lo": min(t0, t1),
        "hi": max(t0, t1),
    }


def _angle_difference(a: float, b: float) -> float:
    d = abs(a - b) % math.pi
    if d > math.pi / 2:
        d = math.pi - d
    return d



def analyse_collinear_overlap(drawing: Drawing) -> dict:
    """
    Return diagnostic statistics only. No geometry is changed.
    """

    data = []
    for obj in drawing.objects:
        if not isinstance(obj, Line):
            continue
        # Colour is fabrication information. Different colours are never
        # considered redundant by this diagnostic.
        if obj.stroke_color is None:
            continue
        item = _segment_data(obj)
        if item is not None:
            data.append(item)

    buckets = defaultdict(list)

    for i, item in enumerate(data):
        angle_bin = round(
            math.degrees(item["theta"]) / ANGLE_BIN_DEG
        )
        offset_bin = round(
            item["c"] / OFFSET_BIN_MM
        )
        buckets[
            (item["line"].stroke_color, angle_bin, offset_bin)
        ].append(i)

    overlap_pairs = []
    seen_pairs = set()
    contained_segments = set()
    parent = list(range(len(data)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        parent[rb] = ra

    # Search neighboring buckets as well as the current bucket.  With a
    # 0.50 mm separation threshold, using only the exact bucket would miss
    # valid pairs that fall on opposite sides of a bucket boundary.
    for (colour, angle_bin, offset_bin), ids in list(buckets.items()):
        if not ids:
            continue

        candidate_ids = []
        for da in (-1, 0, 1):
            for dc in (-1, 0, 1):
                candidate_ids.extend(
                    buckets.get((colour, angle_bin + da, offset_bin + dc), [])
                )

        # De-duplicate candidate indices before interval processing.
        candidate_ids = sorted(set(candidate_ids), key=lambda i: data[i]["lo"])
        if len(candidate_ids) < 2:
            continue

        active = []

        for idx in candidate_ids:
            s = data[idx]

            # Only retain intervals whose end can still overlap this one.
            active = [
                j for j in active
                if data[j]["hi"] >= s["lo"]
            ]

            for j in active:
                if j == idx:
                    continue

                pair_key = (min(j, idx), max(j, idx))
                if pair_key in seen_pairs:
                    continue

                t = data[j]

                angle_deg = math.degrees(
                    _angle_difference(s["theta"], t["theta"])
                )
                if angle_deg > ANGLE_TOL_DEG:
                    continue

                # Exact perpendicular separation between the two supporting
                # lines. The bucket is only a coarse candidate filter.
                ux = math.cos(t["theta"])
                uy = math.sin(t["theta"])
                nx = -uy
                ny = ux

                separation = abs(
                    nx * s["line"].start.x
                    + ny * s["line"].start.y
                    - t["c"]
                )

                if separation > LINE_OFFSET_TOL_MM:
                    continue

                overlap = min(s["hi"], t["hi"]) - max(
                    s["lo"], t["lo"]
                )

                if overlap <= 0:
                    continue

                shorter = min(s["length"], t["length"])
                overlap_ratio = overlap / shorter

                if overlap_ratio < MIN_OVERLAP_RATIO:
                    continue

                seen_pairs.add(pair_key)
                overlap_pairs.append({
                    "a": j,
                    "b": idx,
                    "overlap_mm": overlap,
                    "overlap_ratio": overlap_ratio,
                    "separation_mm": separation,
                    "angle_deg": angle_deg,
                })

                union(j, idx)

                # A segment is "contained" when the overlap is at least 80%
                # of its own length.
                if data[j]["length"] <= data[idx]["length"]:
                    if overlap / data[j]["length"] >= MIN_OVERLAP_RATIO:
                        contained_segments.add(j)
                else:
                    if overlap / data[idx]["length"] >= MIN_OVERLAP_RATIO:
                        contained_segments.add(idx)

            active.append(idx)

    components = defaultdict(list)
    for i in range(len(data)):
        components[find(i)].append(i)

    groups = [
        group
        for group in components.values()
        if len(group) >= 2
    ]

    stack_depth = max((len(g) for g in groups), default=1)

    # Groups where at least one pair is not an exact duplicate are the most
    # interesting for visual inspection.
    exact_duplicate_pairs = 0
    non_exact_groups = []

    def same_endpoints(a: Line, b: Line, tol=0.001):
        direct = (
            math.hypot(a.start.x - b.start.x, a.start.y - b.start.y)
            <= tol
            and
            math.hypot(a.end.x - b.end.x, a.end.y - b.end.y)
            <= tol
        )
        reverse = (
            math.hypot(a.start.x - b.end.x, a.start.y - b.end.y)
            <= tol
            and
            math.hypot(a.end.x - b.start.x, a.end.y - b.start.y)
            <= tol
        )
        return direct or reverse

    for pair in overlap_pairs:
        if same_endpoints(
            data[pair["a"]]["line"],
            data[pair["b"]]["line"],
        ):
            exact_duplicate_pairs += 1

    for group in groups:
        has_non_exact = False
        for n, a in enumerate(group):
            for b in group[n + 1:]:
                if not same_endpoints(
                    data[a]["line"],
                    data[b]["line"],
                ):
                    has_non_exact = True
                    break
            if has_non_exact:
                break
        if has_non_exact:
            non_exact_groups.append(group)

    by_colour = defaultdict(lambda: {
        "pairs": 0,
        "contained": 0,
        "groups": 0,
    })

    for pair in overlap_pairs:
        colour = data[pair["a"]]["line"].stroke_color
        by_colour[colour]["pairs"] += 1

    for i in contained_segments:
        colour = data[i]["line"].stroke_color
        by_colour[colour]["contained"] += 1

    for group in groups:
        colour = data[group[0]]["line"].stroke_color
        by_colour[colour]["groups"] += 1

    return {
        "line_segments": len(data),
        "candidate_buckets": len(buckets),
        "overlap_pairs": len(overlap_pairs),
        "contained_segments": len(contained_segments),
        "groups": len(groups),
        "non_exact_groups": len(non_exact_groups),
        "non_exact_group_indices": non_exact_groups,
        "data": data,
        "max_stack_depth": stack_depth,
        "exact_duplicate_pairs": exact_duplicate_pairs,
        "by_colour": dict(by_colour),
    }


def export_debug_svg(result: dict, path, include_all_lines=True) -> None:
    """Write an SVG visualizing the detected non-exact overlap groups.

    This is diagnostic-only. The source Drawing is never modified.
    Background geometry is shown faintly; each suspicious group is shown
    with a thicker stroke so it can be inspected in Inkscape.
    """
    from pathlib import Path
    from xml.sax.saxutils import escape

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = result.get("data", [])
    groups = result.get("non_exact_group_indices", [])

    if data:
        xs = [p for item in data for p in (item["line"].start.x, item["line"].end.x)]
        ys = [p for item in data for p in (item["line"].start.y, item["line"].end.y)]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
    else:
        min_x = min_y = 0.0
        max_x = max_y = 1.0

    margin = 5.0
    width = max(max_x - min_x + 2 * margin, 1.0)
    height = max(max_y - min_y + 2 * margin, 1.0)

    suspicious = {}
    for group_number, group in enumerate(groups, start=1):
        for idx in group:
            suspicious[idx] = group_number

    # Keep the SVG simple and portable: millimetres, with the same Cartesian
    # coordinate convention used by LaserPrep geometry.
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.4f}mm" height="{height:.4f}mm" viewBox="{min_x-margin:.4f} {min_y-margin:.4f} {width:.4f} {height:.4f}">',
        '<title>LaserPrep collinear overlap diagnostic</title>',
    ]

    if include_all_lines:
        out.append('<g id="background" fill="none" stroke="#cccccc" stroke-width="0.15">')
        for item in data:
            line = item["line"]
            out.append(
                f'<line x1="{line.start.x:.4f}" y1="{line.start.y:.4f}" '
                f'x2="{line.end.x:.4f}" y2="{line.end.y:.4f}" />'
            )
        out.append('</g>')

    out.append('<g id="suspicious-overlaps" fill="none" stroke="#ff00ff" stroke-width="0.7">')
    for idx in suspicious:
        line = data[idx]["line"]
        out.append(
            f'<line x1="{line.start.x:.4f}" y1="{line.start.y:.4f}" '
            f'x2="{line.end.x:.4f}" y2="{line.end.y:.4f}" />'
        )
    out.append('</g>')

    # Small labels at group centroids make it possible to correlate a visual
    # location with a group number if we later add detailed group reporting.
    out.append('<g id="group-labels" font-family="sans-serif" font-size="3" fill="#000000">')
    for group_number, group in enumerate(groups, start=1):
        pts = []
        for idx in group:
            line = data[idx]["line"]
            pts.extend([(line.start.x, line.start.y), (line.end.x, line.end.y)])
        if not pts:
            continue
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        out.append(f'<text x="{cx:.4f}" y="{cy:.4f}">{escape(str(group_number))}</text>')
    out.append('</g>')
    out.append('</svg>')

    path.write_text("\n".join(out), encoding="utf-8")


def format_report(result: dict) -> str:
    lines = [
        "COLLINEAR OVERLAP DIAGNOSTIC",
        "============================================================",
        "",
        f"Line segments analysed       : {result['line_segments']}",
        f"Candidate buckets            : {result['candidate_buckets']}",
        f"Collinear overlap pairs      : {result['overlap_pairs']}",
        f"Contained segments           : {result['contained_segments']}",
        f"Overlap groups               : {result['groups']}",
        f"Non-exact overlap groups     : {result['non_exact_groups']}",
        f"Maximum stack depth          : {result['max_stack_depth']}",
        f"Exact duplicate pairs        : {result['exact_duplicate_pairs']}",
        "",
        "Criteria:",
        f"  Angle tolerance             : {ANGLE_TOL_DEG:.2f}°",
        f"  Line separation             : {LINE_OFFSET_TOL_MM:.2f} mm",
        f"  Minimum segment length      : {MIN_SEGMENT_LENGTH_MM:.2f} mm",
        f"  Minimum overlap             : {MIN_OVERLAP_RATIO:.0%}",
        "",
        "By colour:",
    ]

    for colour, stats in sorted(
        result["by_colour"].items(),
        key=lambda item: str(item[0]),
    ):
        lines.append(
            f"  {colour!s:20s} "
            f"pairs={stats['pairs']:6d} "
            f"contained={stats['contained']:6d} "
            f"groups={stats['groups']:6d}"
        )

    lines.extend([
        "",
        "Diagnostic only: no geometry was modified.",
    ])

    return "\\n".join(lines)
