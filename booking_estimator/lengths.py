"""Numerical length measurement for SVG path segment records."""
from __future__ import annotations

import math


def _distance(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _adaptive_simpson(f, a, b, tolerance=1e-8, max_depth=20):
    """Integrate f over [a,b] using adaptive Simpson quadrature."""
    fa, fb = f(a), f(b)
    midpoint = (a + b) / 2.0
    fm = f(midpoint)
    whole = (b - a) * (fa + 4.0 * fm + fb) / 6.0

    def recurse(left, right, f_left, f_mid, f_right, estimate, tol, depth):
        mid = (left + right) / 2.0
        lmid, rmid = (left + mid) / 2.0, (mid + right) / 2.0
        f_lmid, f_rmid = f(lmid), f(rmid)
        left_est = (mid - left) * (f_left + 4.0 * f_lmid + f_mid) / 6.0
        right_est = (right - mid) * (f_mid + 4.0 * f_rmid + f_right) / 6.0
        combined = left_est + right_est
        error = combined - estimate
        if depth <= 0 or abs(error) <= 15.0 * tol:
            return combined + error / 15.0
        return recurse(left, mid, f_left, f_lmid, f_mid, left_est, tol / 2.0, depth - 1) + recurse(
            mid, right, f_mid, f_rmid, f_right, right_est, tol / 2.0, depth - 1
        )

    return recurse(a, b, fa, fm, fb, whole, tolerance, max_depth)


def segment_length(segment, tolerance=1e-8):
    """Return segment length for line, quadratic, and cubic records.

    Elliptical arc records are intentionally not supported in this phase.
    """
    kind = segment.get("type")
    if kind == "line":
        return _distance(segment["start"], segment["end"])
    if kind not in ("quadratic", "cubic"):
        if kind == "arc":
            raise NotImplementedError("Elliptical arc length is planned for a later stage")
        raise ValueError(f"Unknown segment type: {kind!r}")

    if kind == "quadratic":
        p0, p1, p2 = segment["start"], segment["control"], segment["end"]

        def speed(t):
            dx = 2.0 * ((1-t)*(p1[0]-p0[0]) + t*(p2[0]-p1[0]))
            dy = 2.0 * ((1-t)*(p1[1]-p0[1]) + t*(p2[1]-p1[1]))
            return math.hypot(dx, dy)
    else:
        p0, p1, p2, p3 = segment["start"], segment["control1"], segment["control2"], segment["end"]

        def speed(t):
            u = 1.0 - t
            dx = 3.0*(u*u*(p1[0]-p0[0]) + 2*u*t*(p2[0]-p1[0]) + t*t*(p3[0]-p2[0]))
            dy = 3.0*(u*u*(p1[1]-p0[1]) + 2*u*t*(p2[1]-p1[1]) + t*t*(p3[1]-p2[1]))
            return math.hypot(dx, dy)

    return _adaptive_simpson(speed, 0.0, 1.0, tolerance)


def path_length(segments, tolerance=1e-8):
    """Sum lengths of supported segments in a parsed SVG path."""
    return sum(segment_length(segment, tolerance=tolerance) for segment in segments)
