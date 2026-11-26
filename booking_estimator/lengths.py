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


def _arc_parameters(segment):
    """Convert an SVG endpoint-form arc into center form and angular limits."""
    x1, y1 = segment["start"]
    x2, y2 = segment["end"]
    rx, ry = abs(float(segment["rx"])), abs(float(segment["ry"]))
    rotation = math.radians(float(segment["rotation"]))
    large_arc, sweep = int(segment["large_arc"]), int(segment["sweep"])
    if rx == 0.0 or ry == 0.0 or (x1, y1) == (x2, y2):
        return None
    cos_phi, sin_phi = math.cos(rotation), math.sin(rotation)
    dx, dy = (x1-x2)/2.0, (y1-y2)/2.0
    xp = cos_phi*dx + sin_phi*dy
    yp = -sin_phi*dx + cos_phi*dy
    lam = xp*xp/(rx*rx) + yp*yp/(ry*ry)
    if lam > 1.0:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale
    numerator = max(0.0, rx*rx*ry*ry - rx*rx*yp*yp - ry*ry*xp*xp)
    denominator = rx*rx*yp*yp + ry*ry*xp*xp
    factor = 0.0 if denominator == 0.0 else math.sqrt(numerator/denominator)
    if large_arc == sweep:
        factor = -factor
    cxp = factor*(rx*yp/ry)
    cyp = factor*(-ry*xp/rx)
    cx = cos_phi*cxp - sin_phi*cyp + (x1+x2)/2.0
    cy = sin_phi*cxp + cos_phi*cyp + (y1+y2)/2.0
    ux, uy = (xp-cxp)/rx, (yp-cyp)/ry
    vx, vy = (-xp-cxp)/rx, (-yp-cyp)/ry
    theta1 = math.atan2(uy, ux)
    delta = math.atan2(ux*vy-uy*vx, ux*vx+uy*vy)
    if not sweep and delta > 0:
        delta -= 2.0*math.pi
    elif sweep and delta < 0:
        delta += 2.0*math.pi
    return rx, ry, theta1, delta


def segment_length(segment, tolerance=1e-8):
    """Return segment length for line, quadratic, and cubic records.

    Elliptical arc records are intentionally not supported in this phase.
    """
    kind = segment.get("type")
    if kind == "line":
        return _distance(segment["start"], segment["end"])
    if kind == "arc":
        params = _arc_parameters(segment)
        if params is None:
            return _distance(segment["start"], segment["end"])
        rx, ry, theta1, delta = params
        def arc_speed(theta):
            return math.hypot(rx*math.sin(theta), ry*math.cos(theta))
        return abs(_adaptive_simpson(arc_speed, theta1, theta1+delta, tolerance))
    if kind not in ("quadratic", "cubic"):
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
