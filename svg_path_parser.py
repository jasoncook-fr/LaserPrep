"""
svg_path_parser_v2.py

LaserPrep SVG Path Parser
Version 2.0

Changes from v1.0
-----------------
* One SVG <path> -> one VectorPath.
* Supports compound paths (multiple M...Z contours).
* Z closes the current contour but does NOT end the VectorPath.
"""

from __future__ import annotations

import re

from drawing import Point, Line, Bezier
from vector_path import VectorPath

TOKEN_RE = re.compile(r"[MLCZ]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
COMMANDS = {"M", "L", "C", "Z"}


def tokenize(path_data: str):
    tokens = []
    for t in TOKEN_RE.findall(path_data):
        tokens.append(t if t in COMMANDS else float(t))
    return tokens


def parse_svg_path(
    path_data: str,
    stroke_color=(0, 0, 0),
    stroke_width=0.01,
):
    """
    Parse one SVG path element.

    Returns
    -------
    list[VectorPath]

    Currently returns a list containing a single VectorPath to remain
    compatible with the existing importer. Internally, that VectorPath
    may contain multiple closed contours.
    """

    tokens = tokenize(path_data)

    path = VectorPath()

    current = None
    contour_start = None
    last_cmd = None

    i = 0

    while i < len(tokens):

        tok = tokens[i]

        if isinstance(tok, str):
            cmd = tok
            last_cmd = cmd
            i += 1
        else:
            if last_cmd is None:
                raise RuntimeError("Path starts with coordinates.")
            cmd = last_cmd

        if cmd == "M":

            x = tokens[i]
            y = tokens[i + 1]
            i += 2

            current = Point(x, y)
            contour_start = Point(x, y)

            # Additional coordinate pairs after M become implicit L
            last_cmd = "L"

        elif cmd == "L":

            while i < len(tokens) and not isinstance(tokens[i], str):

                end = Point(tokens[i], tokens[i + 1])
                i += 2

                path.add(
                    Line(
                        current,
                        end,
                        stroke_color,
                        stroke_width,
                    )
                )

                current = end

        elif cmd == "C":

            while i < len(tokens) and not isinstance(tokens[i], str):

                c1 = Point(tokens[i], tokens[i + 1])
                c2 = Point(tokens[i + 2], tokens[i + 3])
                end = Point(tokens[i + 4], tokens[i + 5])
                i += 6

                path.add(
                    Bezier(
                        current,
                        c1,
                        c2,
                        end,
                        stroke_color,
                        stroke_width,
                    )
                )

                current = end

        elif cmd == "Z":

            if (
                current is not None
                and contour_start is not None
                and (
                    current.x != contour_start.x
                    or current.y != contour_start.y
                )
            ):
                path.add(
                    Line(
                        current,
                        Point(contour_start.x, contour_start.y),
                        stroke_color,
                        stroke_width,
                    )
                )

            current = contour_start
            contour_start = None
            last_cmd = None

        else:
            raise NotImplementedError(
                f"Unsupported SVG command: {cmd}"
            )

    if not path.is_empty:
        path.close()

    # Compatibility with existing code.
    return [path]


if __name__ == "__main__":

    sample = (
        "M 0 0 "
        "L 10 0 "
        "L 10 10 "
        "Z "
        "M 3 3 "
        "L 7 3 "
        "L 7 7 "
        "Z"
    )

    paths = parse_svg_path(sample)

    print("SVG PATH PARSER VERSION 2.0")
    print("Returned paths:", len(paths))
    print(paths[0])
    print("Segments:", len(paths[0].objects))


