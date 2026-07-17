#!/usr/bin/env python3
"""
Analyse duplicate imported geometry.

This tool checks whether identical Line objects already exist in
drawing.objects before topology reconstruction.
"""
from collections import defaultdict, Counter

from project import Project
from svg_geometry_import import import_geometry
from text_import import import_text
import sys
# ---------------------------------------------------------------------

PDF_FILE = "input.pdf"      # <-- change this


def point_key(p):
    return (
        round(p.x, 3),
        round(p.y, 3),
    )


def line_key(line):
    """
    Geometry-only key.

    Orientation independent.
    """

    a = point_key(line.start)
    b = point_key(line.end)

    if a > b:
        a, b = b, a

    return (a, b)


# ---------------------------------------------------------------------

project = Project()

project.import_pdf(PDF_FILE)

drawing = project.drawings[0]

import_geometry(drawing)
import_text(drawing)

print()
print("Imported objects")
print("--------------------------------")

print(f"Objects : {len(drawing.objects)}")

# ---------------------------------------------------------------------

groups = defaultdict(list)

for obj in drawing.objects:

    if obj.__class__.__name__ != "Line":
        continue

    groups[line_key(obj)].append(obj)

duplicates = 0
same_colour = 0
mixed_colour = 0
mixed_width = 0

colour_counter = Counter()

print()
print("Duplicate geometry")
print("--------------------------------")

for key, members in groups.items():

    if len(members) == 1:
        continue

    duplicates += len(members) - 1

    colours = {
        tuple(m.stroke_color)
        for m in members
    }

    widths = {
        round(m.stroke_width, 6)
        for m in members
    }

    if len(colours) == 1:
        same_colour += 1
    else:
        mixed_colour += 1

    if len(widths) == 1:
        pass
    else:
        mixed_width += 1

    colour_counter.update(colours)

    print(
        f"{len(members):3d} copies"
        f"    colours={len(colours)}"
        f"    widths={len(widths)}"
    )

# ---------------------------------------------------------------------

print()
print("Summary")
print("--------------------------------")

print(f"Unique line geometries : {len(groups)}")
print(f"Duplicate lines        : {duplicates}")
print(f"Same-colour groups     : {same_colour}")
print(f"Mixed-colour groups    : {mixed_colour}")
print(f"Mixed-width groups     : {mixed_width}")

print()
print("Colours inside duplicate groups")
print("--------------------------------")

for colour, count in colour_counter.items():
    print(f"{colour} : {count}")

# ---------------------------------------------------------------------

print()
print("Examples of mixed-colour duplicates")
print("--------------------------------")

shown = 0

for key, members in groups.items():

    if len(members) < 2:
        continue

    colours = {tuple(m.stroke_color) for m in members}

    if len(colours) == 1:
        continue

    print(f"\nGeometry: {key}")

    for i, m in enumerate(members, start=1):

        print(
            f"  {i:2d}: "
            f"colour={m.stroke_color} "
            f"width={m.stroke_width}"
        )

    shown += 1

    if shown >= 10:
        break

if shown == 0:
    print("No mixed-colour duplicate geometry found.")
