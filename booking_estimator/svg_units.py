"""SVG physical-unit parsing and viewBox-to-mm normalization.

This module intentionally does not perform geometry extraction or runtime prediction.
SVG CSS absolute units use the standard 96 px/in reference.
"""

from __future__ import annotations

import re
from typing import Optional

from .models import SVGDimensions

_MM_PER_UNIT = {
    "mm": 1.0,
    "cm": 10.0,
    "in": 25.4,
    "pt": 25.4 / 72.0,
    "pc": 25.4 / 6.0,
    "px": 25.4 / 96.0,
}
_LENGTH_RE = re.compile(r"^\\s*([+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?)\\s*([a-zA-Z]*)\\s*$")
_VIEWBOX_RE = re.compile(r"[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?")


class SVGUnitError(ValueError):
    """Raised when SVG dimensions cannot safely be resolved."""


def parse_length_mm(value: str) -> float:
    """Parse an SVG length using absolute units and return millimetres."""
    match = _LENGTH_RE.match(str(value))
    if not match:
        raise SVGUnitError(f"Invalid SVG length: {value!r}")
    number, unit = match.groups()
    unit = unit.lower()
    if unit == "":
        # Unitless SVG lengths are user units, treated as CSS px for root dimensions.
        unit = "px"
    if unit not in _MM_PER_UNIT:
        raise SVGUnitError(f"Unsupported or non-absolute SVG unit: {unit!r}")
    result = float(number) * _MM_PER_UNIT[unit]
    if result <= 0:
        raise SVGUnitError("SVG physical dimensions must be positive")
    return result


def parse_viewbox(value: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    """Parse viewBox into (min_x, min_y, width, height)."""
    if value is None or not value.strip():
        return None
    numbers = _VIEWBOX_RE.findall(value)
    # Ensure separators/contents are not silently discarded by the regex.
    residue = _VIEWBOX_RE.sub("", value)
    if residue.replace(",", "").strip():
        raise SVGUnitError(f"Invalid viewBox: {value!r}")
    if len(numbers) != 4:
        raise SVGUnitError(f"viewBox must contain four values: {value!r}")
    vals = tuple(float(n) for n in numbers)
    if vals[2] <= 0 or vals[3] <= 0:
        raise SVGUnitError("viewBox width and height must be positive")
    return vals  # type: ignore[return-value]


def resolve_svg_dimensions(width: Optional[str], height: Optional[str], viewbox: Optional[str]) -> SVGDimensions:
    """Resolve canvas physical dimensions and coordinate-to-mm scale.

    If physical width/height are absent, the viewBox is retained but the canvas is
    considered physically unknown. We deliberately avoid guessing a physical size.
    """
    vb = parse_viewbox(viewbox)
    warnings: list[str] = []
    if width is None or height is None:
        warnings.append("Missing root width or height; physical canvas size is unknown.")
        return SVGDimensions(None, None, vb, None, None, False, warnings)

    w_mm = parse_length_mm(width)
    h_mm = parse_length_mm(height)
    if vb is None:
        # Without viewBox, SVG coordinates use the root's declared dimensions.
        sx = _dimension_user_units_per_mm(width)
        sy = _dimension_user_units_per_mm(height)
        return SVGDimensions(w_mm, h_mm, None, sx, sy, True, warnings)

    _, _, vb_w, vb_h = vb
    sx = w_mm / vb_w
    sy = h_mm / vb_h
    if abs(sx - sy) > max(sx, sy) * 1e-6:
        warnings.append("Canvas aspect ratio differs from viewBox ratio; SVG preserveAspectRatio may introduce non-uniform or unused-space behavior. Geometry normalization requires later preserveAspectRatio handling.")
    return SVGDimensions(w_mm, h_mm, vb, sx, sy, True, warnings)


def _dimension_user_units_per_mm(value: str) -> float:
    match = _LENGTH_RE.match(str(value))
    if not match:
        raise SVGUnitError(f"Invalid SVG length: {value!r}")
    _, unit = match.groups()
    unit = unit.lower() or "px"
    if unit not in _MM_PER_UNIT:
        raise SVGUnitError(f"Unsupported or non-absolute SVG unit: {unit!r}")
    return 1.0 / _MM_PER_UNIT[unit]
