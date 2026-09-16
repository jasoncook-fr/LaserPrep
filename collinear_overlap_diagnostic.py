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

# Secondary test for redundant geometry split into nearly identical fragments.
# The normal test above remains strict; this only applies when both endpoints
# of the two segments are also very close.
FRAGMENTED_MIN_OVERLAP_RATIO = 0.50
FRAGMENTED_ENDPOINT_TOL_MM = 0.25

# Fragmented matches only create a suspicious group when there is more
# than one connected fragmented relationship. This keeps a single
# 50%-overlap coincidence from becoming a group by itself, while still
# catching redundant edges represented by several slightly different
# fragments.
FRAGMENTED_COMPONENT_MIN_EDGES = 2

ENDPOINT_TOL_MM = 0.10


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


def _endpoint_match_distance(a: Line, b: Line) -> float:
    """Return the best worst-case endpoint distance, accounting for reversal."""
    direct = max(
        math.hypot(a.start.x - b.start.x, a.start.y - b.start.y),
        math.hypot(a.end.x - b.end.x, a.end.y - b.end.y),
    )
    reversed_ = max(
        math.hypot(a.start.x - b.end.x, a.start.y - b.end.y),
        math.hypot(a.end.x - b.start.x, a.end.y - b.start.y),
    )
    return min(direct, reversed_)


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
        angle_deg = math.degrees(item["theta"])
        angle_bin = round(angle_deg / ANGLE_BIN_DEG)

        # The supporting-line offset ``c`` in _segment_data() is measured
        # using each line's own angle.  That is geometrically correct for the
        # final separation test, but it is NOT a stable bucket coordinate:
        # even a 0.3° angle difference can shift c by several millimetres
        # when the drawing is hundreds of millimetres from the origin.
        #
        # Use a common reference angle for each bucket instead.  Each line is
        # inserted into the three nearby angle bins, with c recomputed using
        # that bin's centre angle.  Lines that are genuinely near-parallel
        # therefore land in the same offset bucket even when their individual
        # angles differ slightly.
        for target_angle_bin in (angle_bin - 1, angle_bin, angle_bin + 1):
            ref_theta = math.radians(target_angle_bin * ANGLE_BIN_DEG)
            ref_nx = -math.sin(ref_theta)
            ref_ny = math.cos(ref_theta)
            ref_c = (
                ref_nx * item["line"].start.x
                + ref_ny * item["line"].start.y
            )
            offset_bin = round(ref_c / OFFSET_BIN_MM)

            buckets[
                (item["line"].stroke_color, target_angle_bin, offset_bin)
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

                pair_type = None
                endpoint_match_mm = None

                if overlap_ratio >= MIN_OVERLAP_RATIO:
                    pair_type = "normal"
                elif overlap_ratio >= FRAGMENTED_MIN_OVERLAP_RATIO:
                    # A lower overlap threshold is deliberately allowed only
                    # when the two Line objects have matching endpoints. This
                    # catches the common case where the same physical edge was
                    # exported twice as slightly different line fragments,
                    # without globally treating ordinary partial crossings as
                    # redundant.
                    endpoint_match_mm = _endpoint_match_distance(
                        s["line"], t["line"]
                    )
                    if endpoint_match_mm <= FRAGMENTED_ENDPOINT_TOL_MM:
                        pair_type = "fragmented"

                if pair_type is None:
                    continue

                seen_pairs.add(pair_key)
                overlap_pairs.append({
                    "a": j,
                    "b": idx,
                    "overlap_mm": overlap,
                    "overlap_ratio": overlap_ratio,
                    "separation_mm": separation,
                    "angle_deg": angle_deg,
                    "pair_type": pair_type,
                    "endpoint_match_mm": endpoint_match_mm,
                })

                # Normal pairs are always part of the grouping graph.
                # Fragmented pairs are admitted later, after we know whether
                # they form a connected fragmented structure.
                if pair_type == "normal":
                    union(j, idx)

                # A segment is "contained" only under the normal strict
                # overlap rule. Fragmented matches are suspicious, but neither
                # segment is considered contained.
                if pair_type == "normal":
                    if data[j]["length"] <= data[idx]["length"]:
                        if overlap / data[j]["length"] >= MIN_OVERLAP_RATIO:
                            contained_segments.add(j)
                    else:
                        if overlap / data[idx]["length"] >= MIN_OVERLAP_RATIO:
                            contained_segments.add(idx)

            active.append(idx)

    # Fragmented matches are useful when they form a run of at least two
    # relationships. A single fragmented pair is intentionally ignored for
    # grouping because it is too easy for an ordinary partial coincidence
    # to trigger a suspicious group.
    fragmented_parent = list(range(len(data)))

    def fragmented_find(a):
        while fragmented_parent[a] != a:
            fragmented_parent[a] = fragmented_parent[fragmented_parent[a]]
            a = fragmented_parent[a]
        return a

    def fragmented_union(a, b):
        ra, rb = fragmented_find(a), fragmented_find(b)
        if ra == rb:
            return
        fragmented_parent[rb] = ra

    fragmented_pair_indices = []
    for pair_index, pair in enumerate(overlap_pairs):
        if pair.get("pair_type") != "fragmented":
            continue
        a = pair["a"]
        b = pair["b"]
        fragmented_union(a, b)
        fragmented_pair_indices.append(pair_index)

    fragmented_components = defaultdict(list)
    for pair_index in fragmented_pair_indices:
        pair = overlap_pairs[pair_index]
        root = fragmented_find(pair["a"])
        fragmented_components[root].append(pair_index)

    accepted_fragmented_pairs = 0
    for pair_indices in fragmented_components.values():
        if len(pair_indices) < FRAGMENTED_COMPONENT_MIN_EDGES:
            continue
        for pair_index in pair_indices:
            pair = overlap_pairs[pair_index]
            union(pair["a"], pair["b"])
            accepted_fragmented_pairs += 1

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

    def same_endpoints(a: Line, b: Line, tol=ENDPOINT_TOL_MM):
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
                    tol=ENDPOINT_TOL_MM,
                ):
                    has_non_exact = True
                    break
            if has_non_exact:
                break
        if has_non_exact:
            non_exact_groups.append(group)

    # Measure how much of the analysed geometry is actually involved in
    # non-exact overlap. This is more useful than the raw group count alone.
    non_exact_line_indices = {
        idx
        for group in non_exact_groups
        for idx in group
    }
    non_exact_line_segments = len(non_exact_line_indices)
    non_exact_line_ratio = (
        non_exact_line_segments / len(data)
        if data else 0.0
    )

    total_overlap_length_mm = sum(
        pair["overlap_mm"] for pair in overlap_pairs
    )
    normal_pairs = sum(1 for pair in overlap_pairs if pair.get("pair_type") == "normal")
    fragmented_pairs = sum(1 for pair in overlap_pairs if pair.get("pair_type") == "fragmented")

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
        "normal_pairs": normal_pairs,
        "fragmented_pairs": fragmented_pairs,
        "accepted_fragmented_pairs": accepted_fragmented_pairs,
        "fragmented_component_min_edges": FRAGMENTED_COMPONENT_MIN_EDGES,
        "overlap_pair_details": overlap_pairs,
        "contained_segments": len(contained_segments),
        "groups": len(groups),
        "non_exact_groups": len(non_exact_groups),
        "non_exact_group_indices": non_exact_groups,
        "non_exact_line_segments": non_exact_line_segments,
        "non_exact_line_ratio": non_exact_line_ratio,
        "total_overlap_length_mm": total_overlap_length_mm,
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
        f"normal pairs: {result.get('normal_pairs', 0)}",
        f"fragmented pairs detected: {result.get('fragmented_pairs', 0)}",
        f"fragmented pairs accepted into groups: {result.get('accepted_fragmented_pairs', 0)}",
        f"fragmented overlap threshold: {FRAGMENTED_MIN_OVERLAP_RATIO:.2f}",
        f"fragmented endpoint tolerance: {FRAGMENTED_ENDPOINT_TOL_MM:.2f} mm",
        f"fragmented component minimum edges: {FRAGMENTED_COMPONENT_MIN_EDGES}",
        "============================================================",
        "",
        f"Line segments analysed       : {result['line_segments']}",
        f"Candidate buckets            : {result['candidate_buckets']}",
        f"Collinear overlap pairs      : {result['overlap_pairs']}",
        f"Contained segments           : {result['contained_segments']}",
        f"Overlap groups               : {result['groups']}",
        f"Non-exact overlap groups     : {result['non_exact_groups']}",
        f"Lines in non-exact groups    : {result['non_exact_line_segments']}",
        f"Non-exact line ratio         : {result['non_exact_line_ratio']:.2%}",
        f"Total overlap length         : {result['total_overlap_length_mm']:.2f} mm",
        f"Maximum stack depth          : {result['max_stack_depth']}",
        f"Exact duplicate pairs        : {result['exact_duplicate_pairs']}",
        "",
        "Criteria:",
        f"  Angle tolerance             : {ANGLE_TOL_DEG:.2f}°",
        f"  Line separation             : {LINE_OFFSET_TOL_MM:.2f} mm",
        f"  Minimum segment length      : {MIN_SEGMENT_LENGTH_MM:.2f} mm",
        f"  Minimum overlap             : {MIN_OVERLAP_RATIO:.0%}",
        f"  Endpoint tolerance          : {ENDPOINT_TOL_MM:.2f} mm",
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
        "DETAILED NON-EXACT GROUPS",
        "============================================================",
        "Each group lists the individual source Line objects involved.",
        "Coordinates are in the drawing's mm coordinate system.",
        "Pair measurements are reported for detected pairs within the group.",
    ])

    data = result.get("data", [])
    groups = result.get("non_exact_group_indices", [])

    for group_number, group in enumerate(groups, start=1):
        colour = data[group[0]]["line"].stroke_color if data else None
        lines.append(f"\nGROUP {group_number}: {len(group)} lines | colour={colour}")

        xs = [p for idx in group for p in (data[idx]["line"].start.x, data[idx]["line"].end.x)]
        ys = [p for idx in group for p in (data[idx]["line"].start.y, data[idx]["line"].end.y)]
        total_length = sum(data[idx]["length"] for idx in group)
        lines.append(
            f"  bounds=({min(xs):.3f},{min(ys):.3f}) -> ({max(xs):.3f},{max(ys):.3f}) "
            f"total_line_length={total_length:.3f} mm"
        )

        for idx in group:
            line = data[idx]["line"]
            lines.append(
                f"  LINE {idx}: "
                f"start=({line.start.x:.4f},{line.start.y:.4f}) "
                f"end=({line.end.x:.4f},{line.end.y:.4f}) "
                f"length={data[idx]['length']:.4f} mm "
                f"angle={math.degrees(data[idx]['theta']):.4f} deg"
            )

        group_set = set(group)
        group_pairs = [
            pair for pair in result.get("overlap_pair_details", [])
            if pair["a"] in group_set and pair["b"] in group_set
        ]
        if group_pairs:
            lines.append("  DETECTED PAIRS:")
            for pair in group_pairs:
                endpoint_text = (
                    f" endpoint_match={pair['endpoint_match_mm']:.4f} mm"
                    if pair.get('endpoint_match_mm') is not None
                    else ""
                )
                lines.append(
                    f"    {pair['a']} <-> {pair['b']}: "
                    f"type={pair.get('pair_type', 'normal')} "
                    f"overlap={pair['overlap_mm']:.4f} mm "
                    f"ratio={pair['overlap_ratio']:.4f} "
                    f"separation={pair['separation_mm']:.4f} mm "
                    f"angle_diff={pair['angle_deg']:.4f} deg"
                    f"{endpoint_text}"
                )

    lines.extend([
        "",
        "Diagnostic only: no geometry was modified.",
    ])

    return "\n".join(lines)
