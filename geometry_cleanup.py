"""
geometry_cleanup.py

Geometry analysis tools.

Version 0.7.0
"""

from drawing import Drawing, Line
import math

# ============================================================
# REPORT
# ============================================================

class GeometryReport:

    def __init__(self):

        self.zero_length_lines = 0
        self.tiny_lines = 0
        self.duplicate_lines = 0

        # Legacy near-parallel fields retained for report compatibility.
        # The old O(n²) detector is intentionally disabled.
        self.near_parallel_pairs = 0
        self.near_parallel_groups = 0
        self.near_parallel_details = []

        self.shortest_line_mm = None
        self.duplicate_keys = set()

        # Operator report
        self.object_count = 0
        self.path_count = 0
        self.removed_zero_length = 0
        self.removed_duplicates = 0
        self.colours_corrected = 0

        # ATTENTION
        self.near_overlap_candidates = 0

# ============================================================
# ANALYSIS
# ============================================================

def _line_key(line: Line):
    """
    Return a canonical representation of a line including its
    laser-relevant stroke style.

    A→B and B→A produce exactly the same key.
    Coordinates are rounded to 0.001 mm.
    """

    p1 = (
        round(line.start.x, 3),
        round(line.start.y, 3),
    )

    p2 = (
        round(line.end.x, 3),
        round(line.end.y, 3),
    )

    geometry = (p1, p2) if p1 <= p2 else (p2, p1)

    return (
        geometry,
        line.stroke_color,
        line.stroke_width,
    )

# ============================================================
# NEAR-PARALLEL GEOMETRY
# ============================================================

# Fabrication rule:
# Same-colour lines that remain within 1 mm while being
# approximately parallel are considered suspicious.
#
# Different-colour geometry is deliberately ignored.
#
# A short encounter near an acute angle should NOT trigger
# the warning. The lines must remain close over a meaningful
# portion of their length.

NEAR_PARALLEL_DISTANCE_MM = 1.0
NEAR_PARALLEL_ANGLE_DEG = 5.0
NEAR_PARALLEL_MIN_LENGTH_MM = 5.0
NEAR_PARALLEL_CLOSE_FRACTION = 0.80


def _line_length(line: Line) -> float:
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    return math.hypot(dx, dy)


def _line_angle(line: Line) -> float:
    """
    Return the line angle in radians.
    """
    return math.atan2(
        line.end.y - line.start.y,
        line.end.x - line.start.x,
    )


def _angle_difference(a: float, b: float) -> float:
    """
    Return the smallest angle between two lines.

    Lines have no meaningful direction, so 0° and 180°
    are considered equivalent.
    """
    difference = abs(a - b) % math.pi

    if difference > math.pi / 2:
        difference = math.pi - difference

    return difference


def _point_to_segment_distance(px, py, ax, ay, bx, by) -> float:
    """
    Minimum distance from point P to line segment AB.
    """

    dx = bx - ax
    dy = by - ay

    length2 = dx * dx + dy * dy

    if length2 == 0:
        return math.hypot(px - ax, py - ay)

    t = (
        (px - ax) * dx +
        (py - ay) * dy
    ) / length2

    t = max(0.0, min(1.0, t))

    closest_x = ax + t * dx
    closest_y = ay + t * dy

    return math.hypot(
        px - closest_x,
        py - closest_y,
    )


def _sample_close_fraction(
    line_a: Line,
    line_b: Line,
    samples: int = 11,
) -> float:
    """
    Estimate how much of the overlapping portion of two
    approximately parallel lines remains within the
    allowed distance.

    Sampling is intentionally used here rather than a
    complicated exact curve calculation. These are straight
    Line objects, and the detector is diagnostic only.
    """

    ax = line_a.start.x
    ay = line_a.start.y
    bx = line_a.end.x
    by = line_a.end.y

    dx = bx - ax
    dy = by - ay

    length = math.hypot(dx, dy)

    if length == 0:
        return 0.0

    ux = dx / length
    uy = dy / length

    # Project B's endpoints onto A's axis.
    projections = []

    for point in (line_b.start, line_b.end):
        px = point.x - ax
        py = point.y - ay

        projections.append(
            px * ux + py * uy
        )

    overlap_start = max(
        0.0,
        min(projections),
    )

    overlap_end = min(
        length,
        max(projections),
    )

    overlap_length = overlap_end - overlap_start

    if overlap_length <= 0:
        return 0.0

    close = 0

    for i in range(samples):

        if samples == 1:
            distance_along = (
                overlap_start + overlap_end
            ) / 2
        else:
            distance_along = (
                overlap_start
                +
                (overlap_end - overlap_start)
                * i / (samples - 1)
            )

        px = ax + ux * distance_along
        py = ay + uy * distance_along

        distance = _point_to_segment_distance(
            px,
            py,
            line_b.start.x,
            line_b.start.y,
            line_b.end.x,
            line_b.end.y,
        )

        if distance <= NEAR_PARALLEL_DISTANCE_MM:
            close += 1

    return close / samples


def _near_parallel_pair(line_a: Line, line_b: Line):
    """
    Determine whether two lines satisfy the near-parallel
    warning rule.

    Returns diagnostic information or None.
    """

    # Different colours have different fabrication meanings.
    # Never flag them as near-parallel redundancy.
    if line_a.stroke_color != line_b.stroke_color:
        return None

    length_a = _line_length(line_a)
    length_b = _line_length(line_b)

    if (
        length_a < NEAR_PARALLEL_MIN_LENGTH_MM
        or
        length_b < NEAR_PARALLEL_MIN_LENGTH_MM
    ):
        return None

    angle_a = _line_angle(line_a)
    angle_b = _line_angle(line_b)

    angle_difference = _angle_difference(
        angle_a,
        angle_b,
    )

    if math.degrees(angle_difference) > NEAR_PARALLEL_ANGLE_DEG:
        return None

    close_fraction = _sample_close_fraction(
        line_a,
        line_b,
    )

    if close_fraction < NEAR_PARALLEL_CLOSE_FRACTION:
        return None

    return {
        "colour": line_a.stroke_color,
        "separation_mm": min(
            _point_to_segment_distance(
                line_a.start.x,
                line_a.start.y,
                line_b.start.x,
                line_b.start.y,
                line_b.end.x,
                line_b.end.y,
            ),
            _point_to_segment_distance(
                line_a.end.x,
                line_a.end.y,
                line_b.start.x,
                line_b.start.y,
                line_b.end.x,
                line_b.end.y,
            ),
        ),
        "angle_deg": math.degrees(angle_difference),
        "length_a_mm": length_a,
        "length_b_mm": length_b,
        "close_fraction": close_fraction,
    }

def analyse(drawing: Drawing) -> GeometryReport:

    report = GeometryReport()
    report.object_count = len(drawing.objects)

    seen_lines = set()

    lines = [
        obj
        for obj in drawing.objects
        if isinstance(obj, Line)
    ]

    for obj in drawing.objects:

        if not isinstance(obj, Line):
            continue

        key = _line_key(obj)

        if key in seen_lines:

            report.duplicate_lines += 1
            report.duplicate_keys.add(key)

        else:

            seen_lines.add(key)

        dx = obj.end.x - obj.start.x
        dy = obj.end.y - obj.start.y

        length = math.hypot(dx, dy)

        if (
            report.shortest_line_mm is None
            or
            length < report.shortest_line_mm
        ):
            report.shortest_line_mm = length

        length2 = length * length

        length2 = dx * dx + dy * dy

        # Zero-length
        if length2 == 0:
            report.zero_length_lines += 1

        # Tiny segments (0.01 mm)
        elif length2 < (0.01 * 0.01):
            report.tiny_lines += 1


    return report

def remove_zero_length_lines(drawing: Drawing) -> int:
    """
    Remove zero-length Line objects.

    Returns the number removed.
    """

    new_objects = []

    removed = 0

    for obj in drawing.objects:

        if isinstance(obj, Line):

            dx = obj.end.x - obj.start.x
            dy = obj.end.y - obj.start.y

            if dx == 0.0 and dy == 0.0:
                removed += 1
                continue

        new_objects.append(obj)

    drawing.objects = new_objects

    return removed

def remove_duplicate_lines(drawing: Drawing) -> int:
    """
    Remove duplicate Line objects.

    Keeps the last imported duplicate (highest import_order), which
    corresponds to the top-most geometry in the PDF paint order.

    Returns the number removed.
    """

    removed = 0
    latest = {}

    for obj in drawing.objects:

        if not isinstance(obj, Line):
            continue

        key = _line_key(obj)

        if key in latest:
            removed += 1

        latest[key] = obj

    new_objects = []
    emitted = set()

    for obj in drawing.objects:

        if not isinstance(obj, Line):
            new_objects.append(obj)
            continue

        key = _line_key(obj)

        if key in emitted:
            continue

        if latest[key] is obj:
            new_objects.append(obj)
            emitted.add(key)

    drawing.objects = new_objects

    return removed




# ============================================================
# OPERATOR REPORT
# ============================================================

def build_operator_report(report: GeometryReport) -> list[str]:
    """Return human-readable report lines for LaserPrep_Report."""

    lines = [
        "General Information",
        "-------------------------------------",
        f"Objects              : {report.object_count}",
    ]

    if report.path_count:
        lines.append(f"Paths                : {report.path_count}")

    lines.extend([
        "",
        "Cleanup",
        "-------------------------------------",
        f"Removed zero-length  : {report.removed_zero_length}",
        f"Removed duplicates   : {report.removed_duplicates}",
        f"Colours corrected    : {report.colours_corrected}",
    ])

    if report.near_overlap_candidates:
        lines.extend([
            "",
            "ATTENTION",
            "-------------------------------------",
            f"Potential near-overlapping entities : {report.near_overlap_candidates}",
            "These are usually drafting artefacts in the source PDF.",
            "LaserPrep does not automatically merge them.",
        ])

    return lines


