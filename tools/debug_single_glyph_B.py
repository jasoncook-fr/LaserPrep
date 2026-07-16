#!/usr/bin/env python3

import sys
from pathlib import Path
import xml.etree.ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from svg_path_parser import parse_svg_path

INPUT = "TEST_FILES/quarantine/Cartouche_A.text.svg"

tree = ET.parse(INPUT)
root = tree.getroot()

paths = [n for n in root.iter() if n.tag.endswith("path")]

print()
print("=" * 70)
print("MULTI-CONTOUR GLYPHS")
print("=" * 70)

count = 0

for idx, node in enumerate(paths):

    d = node.attrib.get("d", "")

    m_count = d.count("M")

    if m_count < 2:
        continue

    count += 1

    print()
    print("-" * 70)
    print("PATH", idx)
    print("Contours :", m_count)

    parsed = parse_svg_path(d)

    vp = parsed[0]

    print()
    print("Parsed objects")

    for i, obj in enumerate(vp.objects):

        print(
            i,
            type(obj).__name__,
            obj.start,
            "->",
            obj.end
        )

    line_count = 0
    bezier_count = 0

    for obj in vp.objects:

        name = type(obj).__name__

        if name == "Line":
            line_count += 1

        elif name == "Bezier":
            bezier_count += 1

    print("Lines    :", line_count)
    print("Beziers  :", bezier_count)

    #
    # Detect implicit contour transitions.
    #

    pieces = d.split("M")[1:]

    for c, piece in enumerate(pieces):

        closed = "Z" in piece

        print(
            f"  contour {c+1:2d} :",
            "closed" if closed else "OPEN"
        )

print()
print("=" * 70)
print("Multi-contour paths :", count)
print("=" * 70)
