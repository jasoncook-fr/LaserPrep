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
    Return a canonical representation of a line.

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

    if p1 <= p2:
        return (p1, p2)

    return (p2, p1)

def analyse(drawing: Drawing) -> GeometryReport:

    report = GeometryReport()
    report.object_count = len(drawing.objects)

    seen_lines = set()

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


