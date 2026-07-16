#!/usr/bin/env python3

import xml.etree.ElementTree as ET

from svg_path_parser import parse_svg_path
from svg_writer import _path_to_svg_d   # use your existing helper if present

SVG_NS = "{http://www.w3.org/2000/svg}"

INPUT = "Cartouche_A.text.svg"
OUTPUT = "glyph_debug.svg"

tree = ET.parse(INPUT)
root = tree.getroot()

# Pick a path manually.
# Change INDEX until you hit the ENSAM "A".
INDEX = 0

paths = [n for n in root.iter() if n.tag.endswith("path")]

node = paths[INDEX]

d = node.attrib["d"]

print("=" * 60)
print("ORIGINAL SVG PATH")
print("=" * 60)
print(d)

parsed = parse_svg_path(d)

print()
print("Returned VectorPaths :", len(parsed))
print("Objects :", len(parsed[0].objects))

svg_d = _path_to_svg_d(parsed[0])

with open(OUTPUT, "w") as f:

    f.write("""<svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 300 300">\n""")

    f.write(
        f'<path d="{svg_d}" '
        'fill="none" '
        'stroke="black" '
        'stroke-width="0.2"/>\n'
    )

    f.write("</svg>\n")

print()
print("Written", OUTPUT)
