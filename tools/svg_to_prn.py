#!/usr/bin/env python3
"""
svg_to_prn.py — first real SVG/Inkscape -> LTT PRN converter.

This version targets the vector format we reverse-engineered from the
Windows-generated PRN files:

    PSPA  absolute start position (machine units)
    PDPR  first relative move with the laser down
    PR    subsequent relative moves
    PU    laser up / end of path

Machine coordinates:
    1 machine unit = 0.001 inch = 0.0254 mm
    X increases to the right.
    Y increases upward in SVG, but the PRN coordinate system has its
    origin at the bottom-left of the page, so:
        machine_y = page_height_machine - svg_y_machine

The Windows exporter rounds coordinates to integer machine units.

Supported SVG geometry in this first version:
    <line>, <rect>, <polyline>, <polygon>, and <path>
    Path commands: M/m, L/l, H/h, V/v, Z/z

Curves (C, S, Q, T, A) are deliberately rejected for now rather than
silently approximated.

The header before the first PSPA is copied from a known-good Windows PRN.
The footer checksum is the 16-bit sum of all bytes before the checksum,
and the final 4 bytes are the total file length (both big-endian).

Usage:
    python3 svg_to_prn.py reference.prn drawing.svg output.prn

Example:
    python3 svg_to_prn.py test-geometry-WIN.prn test-geometry.svg test-out.prn
"""

from __future__ import annotations

import math
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


MACHINE_PER_MM = 1000.0 / 25.4  # 39.37007874015748


# ---------------------------------------------------------------------------
# Binary helpers
# ---------------------------------------------------------------------------

def pack_s32(n: int) -> bytes:
    return struct.pack(">i", int(n))


def record(tag: bytes, x: int, y: int) -> bytes:
    return tag + pack_s32(x) + pack_s32(y)


def find_tag(data: bytes, tag: bytes, start: int = 0) -> int:
    i = data.find(tag, start)
    if i < 0:
        raise ValueError(f"Could not find {tag!r} in reference PRN")
    return i


# ---------------------------------------------------------------------------
# SVG units / transforms
# ---------------------------------------------------------------------------

UNIT_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
    "pt": 25.4 / 72.0,
    "pc": 25.4 / 6.0,
    "px": 25.4 / 96.0,
}


def parse_length(value: str) -> float:
    """Return a physical SVG length in mm."""
    value = value.strip()
    m = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)", value)
    if not m:
        raise ValueError(f"Cannot parse SVG length: {value!r}")
    number = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "%":
        raise ValueError("Percentage page dimensions are not supported")
    if unit == "":
        # SVG's unitless root width/height is normally px, but Inkscape
        # files with an explicit viewBox commonly pair these with mm.
        # We only use this as a fallback.
        return number * UNIT_TO_MM["px"]
    if unit not in UNIT_TO_MM:
        raise ValueError(f"Unsupported SVG unit: {unit!r}")
    return number * UNIT_TO_MM[unit]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_viewbox(root: ET.Element):
    vb = root.get("viewBox")
    if not vb:
        raise ValueError("SVG must have a viewBox")
    nums = [float(x) for x in re.findall(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", vb
    )]
    if len(nums) != 4:
        raise ValueError(f"Bad viewBox: {vb!r}")
    return nums  # min_x, min_y, width, height


def matrix_mul(a, b):
    """Multiply 2D affine matrices represented as (a,b,c,d,e,f)."""
    a1, b1, c1, d1, e1, f1 = a
    a2, b2, c2, d2, e2, f2 = b
    return (
        a1*a2 + c1*b2,
        b1*a2 + d1*b2,
        a1*c2 + c1*d2,
        b1*c2 + d1*d2,
        a1*e2 + c1*f2 + e1,
        b1*e2 + d1*f2 + f1,
    )


def apply_matrix(m, x, y):
    a, b, c, d, e, f = m
    return (a*x + c*y + e, b*x + d*y + f)


def parse_transform(s: str | None):
    if not s:
        return (1, 0, 0, 1, 0, 0)

    result = (1, 0, 0, 1, 0, 0)

    for name, args_s in re.findall(r"([a-zA-Z]+)\s*\(([^)]*)\)", s):
        vals = [
            float(x) for x in re.findall(
                r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",
                args_s
            )
        ]
        name = name.lower()

        if name == "matrix":
            if len(vals) != 6:
                raise ValueError(f"Bad matrix() transform: {s!r}")
            m = tuple(vals)

        elif name == "translate":
            if len(vals) not in (1, 2):
                raise ValueError(f"Bad translate() transform: {s!r}")
            m = (1, 0, 0, 1, vals[0], vals[1] if len(vals) == 2 else 0)

        elif name == "scale":
            if len(vals) not in (1, 2):
                raise ValueError(f"Bad scale() transform: {s!r}")
            sx = vals[0]
            sy = vals[1] if len(vals) == 2 else sx
            m = (sx, 0, 0, sy, 0, 0)

        elif name == "rotate":
            if len(vals) not in (1, 3):
                raise ValueError(f"Bad rotate() transform: {s!r}")
            angle = math.radians(vals[0])
            ca, sa = math.cos(angle), math.sin(angle)
            r = (ca, sa, -sa, ca, 0, 0)
            if len(vals) == 1:
                m = r
            else:
                cx, cy = vals[1], vals[2]
                m = matrix_mul(
                    matrix_mul((1, 0, 0, 1, cx, cy), r),
                    (1, 0, 0, 1, -cx, -cy),
                )

        elif name == "skewx":
            if len(vals) != 1:
                raise ValueError(f"Bad skewX() transform: {s!r}")
            m = (1, 0, math.tan(math.radians(vals[0])), 1, 0, 0)

        elif name == "skewy":
            if len(vals) != 1:
                raise ValueError(f"Bad skewY() transform: {s!r}")
            m = (1, math.tan(math.radians(vals[0])), 0, 1, 0, 0)

        else:
            raise ValueError(f"Unsupported transform: {name}")

        # SVG transform lists are applied in sequence.
        result = matrix_mul(result, m)

    return result


# ---------------------------------------------------------------------------
# SVG path parser
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(
    r"[AaCcHhLlMmQqSsTtVvZz]|"
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
)


def tokenize_path(d: str):
    return TOKEN_RE.findall(d)


PARAMS = {
    "M": 2, "L": 2, "H": 1, "V": 1,
    "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7,
    "Z": 0,
}


def parse_path(d: str):
    """
    Return a list of subpaths, each a list of (x, y).

    Only straight-line path commands are accepted.
    """
    tokens = tokenize_path(d)
    i = 0
    cmd = None
    x = y = 0.0
    start_x = start_y = 0.0
    subpaths = []
    current = None

    def is_command(tok):
        return len(tok) == 1 and tok.isalpha()

    while i < len(tokens):
        if is_command(tokens[i]):
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if current is not None and (x != start_x or y != start_y):
                    current.append((start_x, start_y))
                if current is not None:
                    subpaths.append(current)
                    current = None
                x, y = start_x, start_y
                cmd = None
                continue

        if cmd is None:
            raise ValueError("Malformed SVG path")

        upper = cmd.upper()
        n = PARAMS[upper]

        if upper in "CSTAQ":
            raise ValueError(
                f"Curved SVG path command {cmd!r} encountered. "
                "This first converter supports straight paths only."
            )

        if i + n > len(tokens) or any(is_command(t) for t in tokens[i:i+n]):
            raise ValueError(f"Missing parameters for path command {cmd!r}")

        vals = [float(t) for t in tokens[i:i+n]]
        i += n
        rel = cmd.islower()

        if upper == "M":
            nx, ny = vals
            if rel:
                nx += x
                ny += y

            if current is not None:
                subpaths.append(current)

            current = [(nx, ny)]
            x, y = nx, ny
            start_x, start_y = x, y

            # Subsequent coordinate pairs after M are implicit L commands.
            cmd = "l" if rel else "L"

        elif upper == "L":
            nx, ny = vals
            if rel:
                nx += x
                ny += y
            current.append((nx, ny))
            x, y = nx, ny

        elif upper == "H":
            nx = vals[0] + x if rel else vals[0]
            current.append((nx, y))
            x = nx

        elif upper == "V":
            ny = vals[0] + y if rel else vals[0]
            current.append((x, ny))
            y = ny

    if current is not None:
        subpaths.append(current)

    return subpaths


# ---------------------------------------------------------------------------
# SVG geometry extraction
# ---------------------------------------------------------------------------

def numbers(s):
    return [
        float(x) for x in re.findall(
            r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",
            s or ""
        )
    ]


def points_attr(s):
    vals = numbers(s)
    if len(vals) % 2:
        raise ValueError("Odd number of coordinates in points attribute")
    return list(zip(vals[0::2], vals[1::2]))


def element_subpaths(elem: ET.Element):
    tag = local_name(elem.tag)

    if tag == "path":
        return parse_path(elem.get("d", ""))

    if tag == "line":
        return [[
            (float(elem.get("x1", 0)), float(elem.get("y1", 0))),
            (float(elem.get("x2", 0)), float(elem.get("y2", 0))),
        ]]

    if tag == "rect":
        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        w = float(elem.get("width", 0))
        h = float(elem.get("height", 0))
        if w <= 0 or h <= 0:
            return []
        return [[
            (x, y),
            (x + w, y),
            (x + w, y + h),
            (x, y + h),
            (x, y),
        ]]

    if tag in ("polyline", "polygon"):
        pts = points_attr(elem.get("points", ""))
        if tag == "polygon" and pts and pts[-1] != pts[0]:
            pts.append(pts[0])
        return [pts] if len(pts) >= 2 else []

    return []


def collect_geometry(root):
    geometry = []

    def walk(elem, parent_matrix):
        own = parse_transform(elem.get("transform"))
        matrix = matrix_mul(parent_matrix, own)

        if local_name(elem.tag) in {"path", "line", "rect", "polyline", "polygon"}:
            for subpath in element_subpaths(elem):
                if len(subpath) >= 2:
                    geometry.append([
                        apply_matrix(matrix, x, y) for x, y in subpath
                    ])

        for child in elem:
            walk(child, matrix)

    walk(root, (1, 0, 0, 1, 0, 0))
    return geometry


# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------

def round_delta(v: float) -> int:
    """Round a relative machine-unit delta to the nearest integer."""
    if v >= 0:
        return int(math.floor(v + 0.5))
    return int(math.ceil(v - 0.5))


def absolute_machine_x(v_mm: float) -> int:
    # The Windows exporter observations from our reference files match
    # truncation for absolute X coordinates.
    return int(math.floor(v_mm * MACHINE_PER_MM))


def absolute_machine_y(v_mm: float) -> int:
    # The Windows exporter observations from the reference PRN match
    # ceiling for absolute Y coordinates.
    return int(math.ceil(v_mm * MACHINE_PER_MM))


def svg_to_machine(points, root, page_height_mm, viewbox):
    min_x, min_y, vb_w, vb_h = viewbox

    # Root physical dimensions define the scale from viewBox units to mm.
    width_mm = parse_length(root.get("width", f"{vb_w}px"))
    height_mm = parse_length(root.get("height", f"{vb_h}px"))

    sx = width_mm / vb_w
    sy = height_mm / vb_h

    out = []
    for x, y in points:
        x_mm = (x - min_x) * sx
        y_mm = (y - min_y) * sy

        mx = absolute_machine_x(x_mm)
        my = absolute_machine_y(page_height_mm - y_mm)

        out.append((mx, my))
    return out


# ---------------------------------------------------------------------------
# PRN construction
# ---------------------------------------------------------------------------

def extract_envelope(reference: bytes):
    pspa = find_tag(reference, b"PSPA")
    footer = reference.rfind(b"\x1bBYE")
    if footer < 0:
        raise ValueError("Could not find BYE footer in reference PRN")

    header = reference[:pspa]
    trailer = reference[footer:]

    if len(trailer) < 8:
        raise ValueError("Reference footer is unexpectedly short")

    return header, trailer


def build_prn(reference_path, svg_path):
    reference = Path(reference_path).read_bytes()
    header, trailer = extract_envelope(reference)

    root = ET.parse(svg_path).getroot()
    viewbox = parse_viewbox(root)
    _, _, vb_w, vb_h = viewbox

    width_mm = parse_length(root.get("width", f"{vb_w}px"))
    height_mm = parse_length(root.get("height", f"{vb_h}px"))

    geometry = collect_geometry(root)

    if not geometry:
        raise ValueError("No supported vector geometry found in SVG")

    records = bytearray()

    for points in geometry:
        machine_points = svg_to_machine(
            points, root, height_mm, viewbox
        )

        # Remove consecutive duplicate machine points.
        cleaned = []
        for p in machine_points:
            if not cleaned or p != cleaned[-1]:
                cleaned.append(p)

        if len(cleaned) < 2:
            continue

        x0, y0 = cleaned[0]
        records += b"PSPA" + pack_s32(x0) + pack_s32(y0)

        # First movement is PDPR.
        x1, y1 = cleaned[1]
        records += record(b"PDPR", round_delta(x1 - x0), round_delta(y1 - y0))

        # Remaining movements are PR.
        prev_x, prev_y = x1, y1
        for x, y in cleaned[2:]:
            records += record(b"PR", round_delta(x - prev_x), round_delta(y - prev_y))
            prev_x, prev_y = x, y

        records += b"PU"

    if not records:
        raise ValueError("No drawable geometry remained after conversion")

    # The Windows PRN's trailer is:
    #   1b 42 59 45
    #   2-byte checksum
    #   4-byte total file length
    #
    # Rebuild it rather than copying the reference checksum/length.
    prefix = header + records + b"\x1bBYE"
    checksum = sum(prefix) & 0xFFFF

    total_length = len(prefix) + 2 + 4
    return (
        prefix
        + struct.pack(">H", checksum)
        + struct.pack(">I", total_length)
    )


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 svg_to_prn.py "
            "reference.prn input.svg output.prn"
        )
        raise SystemExit(2)

    reference, svg, output = sys.argv[1:]

    data = build_prn(reference, svg)
    Path(output).write_bytes(data)

    print(f"Wrote {output}")
    print(f"  size: {len(data)} bytes")
    print(f"  checksum: 0x{int.from_bytes(data[-6:-4], 'big'):04x}")
    print(f"  length field: {int.from_bytes(data[-4:], 'big')}")


if __name__ == "__main__":
    main()
