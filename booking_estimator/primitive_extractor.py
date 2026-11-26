"""Basic SVG shape extraction with inherited group transforms and styles.

This first extractor handles geometric primitives only. Path data and viewport
normalization are intentionally deferred to subsequent stages.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from .geometry import GeometryRecord, Matrix
from .transforms import parse_transform_list
from .path_parser import parse_path_data
from .svg_units import _MM_PER_UNIT

SUPPORTED = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path"}
STYLE_KEYS = {"fill", "stroke", "stroke-width", "opacity", "fill-opacity",
              "stroke-opacity", "stroke-linecap", "stroke-linejoin",
              "stroke-dasharray", "visibility", "display"}
_NUM = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_POINT_SEP = re.compile(r"[\s,]+")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _number(value: str | None, default: float = 0.0) -> float:
    """Parse primitive SVG lengths into user units (CSS px for absolute units).

    Unitless values remain SVG user units. Absolute units are converted to
    equivalent CSS px user units. Percentage and font-relative units are
    deliberately unsupported here.
    """
    if value is None:
        return default
    raw=value.strip()
    match=_NUM.match(raw)
    if not match:
        raise ValueError(f"Invalid primitive numeric value: {value!r}")
    number=float(match.group(0)); unit=raw[match.end():].strip().lower()
    if not math.isfinite(number):
        raise ValueError("SVG geometry values must be finite")
    if not unit:
        return number
    if unit not in _MM_PER_UNIT:
        raise ValueError(f"Unsupported SVG geometry unit: {unit!r}")
    return number*_MM_PER_UNIT[unit]/_MM_PER_UNIT["px"]


def _parse_style(element: ET.Element, inherited: dict[str, str]) -> dict[str, str]:
    style = dict(inherited)
    for key in STYLE_KEYS:
        if key in element.attrib:
            style[key] = element.attrib[key]
    inline = element.attrib.get("style", "")
    for part in inline.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = key.strip()
        if key in STYLE_KEYS:
            style[key] = value.strip()
    return style


def _parse_points(text: str) -> list[tuple[float, float]]:
    raw = text.strip()
    if not raw:
        return []
    tokens = [t for t in _POINT_SEP.split(raw) if t]
    if len(tokens) % 2:
        raise ValueError("points attribute must contain coordinate pairs")
    if not all(_NUM.fullmatch(t) for t in tokens):
        raise ValueError(f"Invalid points attribute: {text!r}")
    vals = [float(t) for t in tokens]
    if not all(math.isfinite(v) for v in vals):
        raise ValueError("Point coordinates must be finite")
    return [(vals[i], vals[i+1]) for i in range(0, len(vals), 2)]


def _shape_payload(tag: str, attrs: dict[str, str]) -> dict[str, object]:
    if tag == "path":
        return {"segments": parse_path_data(attrs.get("d", ""))}
    if tag == "rect":
        payload = {k: _number(attrs.get(k)) for k in ("x", "y", "width", "height")}
        payload["rx"] = _number(attrs.get("rx"), _number(attrs.get("ry"))) if attrs.get("rx") is not None else _number(attrs.get("ry"))
        payload["ry"] = _number(attrs.get("ry"), _number(attrs.get("rx"))) if attrs.get("ry") is not None else _number(attrs.get("rx"))
        if payload["width"] < 0 or payload["height"] < 0:
            raise ValueError("rect width and height must not be negative")
        return payload
    if tag in {"circle", "ellipse"}:
        keys = ("cx", "cy", "r") if tag == "circle" else ("cx", "cy", "rx", "ry")
        payload = {k: _number(attrs.get(k)) for k in keys}
        if any(payload[k] < 0 for k in keys if k in ("r", "rx", "ry")):
            raise ValueError(f"{tag} radii must not be negative")
        return payload
    if tag == "line":
        return {k: _number(attrs.get(k)) for k in ("x1", "y1", "x2", "y2")}
    if tag in {"polyline", "polygon"}:
        return {"points": _parse_points(attrs.get("points", ""))}
    raise ValueError(f"Unsupported shape: {tag}")


def extract_basic_shapes(svg_source: str) -> list[GeometryRecord]:
    """Extract supported primitive records from an SVG string.

    Group transforms and style inheritance are retained on each record.
    Records are not yet converted to millimetres or analyzed for cut/engrave
    operations.
    """
    try:
        root = ET.fromstring(svg_source)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed SVG/XML: {exc}") from exc

    records: list[GeometryRecord] = []

    def walk(node: ET.Element, parent_matrix: Matrix, parent_style: dict[str, str]):
        tag = _local(node.tag)
        own_transform = parse_transform_list(node.attrib.get("transform", ""))
        matrix = parent_matrix.compose(own_transform)
        style = _parse_style(node, parent_style)

        if tag in SUPPORTED:
            payload = _shape_payload(tag, node.attrib)
            records.append(GeometryRecord(
                element_type=tag,
                payload=payload,
                source_id=node.attrib.get("id"),
                source_element=node.tag,
                transform=matrix,
                style=style,
            ))
        elif tag not in {"svg", "g", "defs", "symbol", "clipPath", "mask"} and tag not in {"path", "text", "image", "use"}:
            # Unsupported elements are ignored at this stage.
            pass

        if tag in {"defs", "symbol", "clipPath", "mask"}:
            return
        for child in node:
            walk(child, matrix, style)

    walk(root, Matrix(), {})
    return records
