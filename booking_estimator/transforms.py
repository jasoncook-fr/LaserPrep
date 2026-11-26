"""Parsing and composing SVG transform-list syntax.

SVG transform lists are accumulated left-to-right as matrix composition, with
each later transform applied to a point before the accumulated earlier matrix.
"""
from __future__ import annotations

import math
import re

from .geometry import Matrix

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_FUNC_RE = re.compile(r"([A-Za-z]+)\s*\(([^()]*)\)")
_NUM_RE = re.compile(_NUMBER)


def _parse_numbers(text: str) -> list[float]:
    text = text.strip()
    if not text:
        return []
    tokens = []
    pos = 0
    while pos < len(text):
        while pos < len(text) and (text[pos].isspace() or text[pos] == ","):
            pos += 1
        if pos >= len(text):
            break
        match = _NUM_RE.match(text, pos)
        if not match:
            raise ValueError(f"Invalid numeric arguments: {text!r}")
        tokens.append(float(match.group()))
        pos = match.end()
        # A comma must not be repeated or trail the list.
        if pos < len(text) and text[pos] == ",":
            pos += 1
            if pos == len(text) or text[pos] == ",":
                raise ValueError(f"Invalid numeric separators: {text!r}")
    return tokens


def parse_transform_function(name: str, args: list[float]) -> Matrix:
    name = name.strip()
    if name == "matrix":
        if len(args) != 6:
            raise ValueError("matrix() requires exactly 6 arguments")
        return Matrix(*args)
    if name == "translate":
        if len(args) not in (1, 2):
            raise ValueError("translate() requires 1 or 2 arguments")
        return Matrix(e=args[0], f=args[1] if len(args) == 2 else 0.0)
    if name == "scale":
        if len(args) not in (1, 2):
            raise ValueError("scale() requires 1 or 2 arguments")
        return Matrix(a=args[0], d=args[1] if len(args) == 2 else args[0])
    if name == "rotate":
        if len(args) not in (1, 3):
            raise ValueError("rotate() requires 1 or 3 arguments")
        theta = math.radians(args[0])
        c, s = math.cos(theta), math.sin(theta)
        rotation = Matrix(c, s, -s, c)
        if len(args) == 3:
            cx, cy = args[1], args[2]
            return Matrix(e=cx, f=cy).compose(rotation).compose(Matrix(e=-cx, f=-cy))
        return rotation
    if name == "skewX":
        if len(args) != 1:
            raise ValueError("skewX() requires exactly 1 argument")
        tangent = math.tan(math.radians(args[0]))
        if not math.isfinite(tangent):
            raise ValueError("skewX angle produces a non-finite transform")
        return Matrix(c=tangent)
    if name == "skewY":
        if len(args) != 1:
            raise ValueError("skewY() requires exactly 1 argument")
        tangent = math.tan(math.radians(args[0]))
        if not math.isfinite(tangent):
            raise ValueError("skewY angle produces a non-finite transform")
        return Matrix(b=tangent)
    raise ValueError(f"Unsupported SVG transform: {name}")


def parse_transform_list(text: str) -> Matrix:
    """Parse a full SVG transform attribute and return its combined matrix."""
    if not text or not text.strip():
        return Matrix()

    pos = 0
    transforms: list[Matrix] = []
    while pos < len(text):
        while pos < len(text) and (text[pos].isspace() or text[pos] == ","):
            pos += 1
        if pos == len(text):
            break
        match = _FUNC_RE.match(text, pos)
        if not match:
            raise ValueError(f"Malformed transform list near {text[pos:]!r}")
        name, arg_text = match.groups()
        args = _parse_numbers(arg_text)
        transforms.append(parse_transform_function(name, args))
        pos = match.end()

    combined = Matrix()
    for transform in transforms:
        combined = combined.compose(transform)
    return combined
