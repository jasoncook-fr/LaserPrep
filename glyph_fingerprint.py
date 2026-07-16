"""
glyph_fingerprint_B.py

Creates stable fingerprints for VectorPaths.

Version B:
- Translation invariant
- Keeps original scale
- Quantises coordinates to 0.01 mm
- Includes bounding-box dimensions
"""

from __future__ import annotations

import hashlib

from drawing import Line, Bezier


#
# Laser accuracy is nowhere near 0.01 mm.
# Quantising to two decimals removes floating-point noise.
#
ROUND_DIGITS = 2


def _round(value: float) -> float:
    return round(value, ROUND_DIGITS)


def _all_points(vpath):

    for obj in vpath:

        if isinstance(obj, Line):

            yield obj.start
            yield obj.end

        elif isinstance(obj, Bezier):

            yield obj.start
            yield obj.control1
            yield obj.control2
            yield obj.end


def _bounding_box(vpath):

    xs = []
    ys = []

    for pt in _all_points(vpath):

        xs.append(pt.x)
        ys.append(pt.y)

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    )


def canonical_geometry(vpath):

    left, top, right, bottom = _bounding_box(vpath)

    width = right - left
    height = bottom - top

    records = []

    #
    # Store glyph dimensions.
    #
    records.append(
        (
            "SIZE",
            _round(width),
            _round(height),
        )
    )

    for obj in vpath:

        if isinstance(obj, Line):

            records.append(
                (
                    "L",
                    _round(obj.start.x - left),
                    _round(obj.start.y - top),
                    _round(obj.end.x - left),
                    _round(obj.end.y - top),
                )
            )

        elif isinstance(obj, Bezier):

            records.append(
                (
                    "C",
                    _round(obj.start.x - left),
                    _round(obj.start.y - top),
                    _round(obj.control1.x - left),
                    _round(obj.control1.y - top),
                    _round(obj.control2.x - left),
                    _round(obj.control2.y - top),
                    _round(obj.end.x - left),
                    _round(obj.end.y - top),
                )
            )

    return tuple(records)


def fingerprint(vpath):

    canonical = repr(canonical_geometry(vpath)).encode("utf-8")

    return hashlib.sha1(canonical).hexdigest()


def compare(a, b):

    return canonical_geometry(a) == canonical_geometry(b)
