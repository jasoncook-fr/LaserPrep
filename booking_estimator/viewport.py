"""SVG viewBox and preserveAspectRatio mapping into physical viewport coordinates."""
from __future__ import annotations

from .geometry import Matrix
from .svg_units import SVGUnitError, parse_viewbox, parse_length_mm

_ALIGN = {
    "xMinYMin": (0.0, 0.0), "xMidYMin": (0.5, 0.0), "xMaxYMin": (1.0, 0.0),
    "xMinYMid": (0.0, 0.5), "xMidYMid": (0.5, 0.5), "xMaxYMid": (1.0, 0.5),
    "xMinYMax": (0.0, 1.0), "xMidYMax": (0.5, 1.0), "xMaxYMax": (1.0, 1.0),
}


def viewbox_to_viewport_matrix(viewbox: str | tuple[float, float, float, float],
                               width: str, height: str,
                               preserve_aspect_ratio: str | None = None) -> Matrix:
    """Return a mapping from viewBox user coordinates into viewport millimetres.

    Implements SVG preserveAspectRatio alignment and meet/slice behavior.
    Viewport dimensions are absolute physical lengths. The default is xMidYMid meet.
    """
    vb = parse_viewbox(viewbox) if isinstance(viewbox, str) else viewbox
    if vb is None:
        raise SVGUnitError("A viewBox is required for viewport normalization")
    x0, y0, vbw, vbh = vb
    wmm, hmm = parse_length_mm(width), parse_length_mm(height)
    sx, sy = wmm / vbw, hmm / vbh
    tokens = (preserve_aspect_ratio or "xMidYMid meet").strip().split()
    if tokens and tokens[0] == "defer":
        tokens = tokens[1:]
    if not tokens:
        tokens = ["xMidYMid", "meet"]
    align = tokens[0]
    if align == "none":
        if len(tokens) > 1:
            raise SVGUnitError("preserveAspectRatio none does not accept meet/slice")
        return Matrix(sx, 0, 0, sy, -x0*sx, -y0*sy)
    if align not in _ALIGN:
        raise SVGUnitError(f"Invalid preserveAspectRatio alignment: {align!r}")
    mode = tokens[1] if len(tokens) > 1 else "meet"
    if mode not in ("meet", "slice") or len(tokens) > 2:
        raise SVGUnitError(f"Invalid preserveAspectRatio mode: {mode!r}")
    scale = min(sx, sy) if mode == "meet" else max(sx, sy)
    scaled_w, scaled_h = vbw*scale, vbh*scale
    ax, ay = _ALIGN[align]
    offset_x, offset_y = (wmm-scaled_w)*ax, (hmm-scaled_h)*ay
    return Matrix(scale, 0, 0, scale, offset_x-x0*scale, offset_y-y0*scale)
