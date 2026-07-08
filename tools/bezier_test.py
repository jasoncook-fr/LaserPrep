#!/usr/bin/env python3

import sys
import fitz


def rgb_to_hex(col):
    r = int(round(col[0] * 255))
    g = int(round(col[1] * 255))
    b = int(round(col[2] * 255))
    return f"#{r:02X}{g:02X}{b:02X}"


if len(sys.argv) != 3:
    print("Usage:")
    print("    python tools/bezier_test.py input.pdf output.svg")
    sys.exit(1)

pdf_name = sys.argv[1]
svg_name = sys.argv[2]

doc = fitz.open(pdf_name)
page = doc[0]

drawings = page.get_drawings()

# Drawing 1 is the page rectangle.
drawing = drawings[1]
rect = page.rect

def make_path(flip_y=False):
    d = []
    first = True

    for item in drawing["items"]:

        if item[0] != "c":
            continue

        p0 = item[1]
        c1 = item[2]
        c2 = item[3]
        p1 = item[4]

        def Y(y):
            return rect.height - y if flip_y else y

        if first:
            d.append(f"M {p0.x:.3f},{Y(p0.y):.3f}")
            first = False

        d.append(
            f"C "
            f"{c1.x:.3f},{Y(c1.y):.3f} "
            f"{c2.x:.3f},{Y(c2.y):.3f} "
            f"{p1.x:.3f},{Y(p1.y):.3f}"
        )

    return " ".join(d)


blue_path = make_path(False)
red_path = make_path(True)

svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{rect.width}"
     height="{rect.height}"
     viewBox="0 0 {rect.width} {rect.height}">

<path
    d="{blue_path}"
    fill="none"
    stroke="blue"
    stroke-width="2"/>

<path
    d="{red_path}"
    fill="none"
    stroke="red"
    stroke-width="2"/>

</svg>
"""

with open(svg_name, "w") as f:
    f.write(svg)

print("Done.")
