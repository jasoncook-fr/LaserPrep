#!/usr/bin/env python3

from pathlib import Path

from drawing import Drawing
from svg_text_import import import_svg_paths
from svg_writer import write_debug_svg


# ------------------------------------------------------------
# INPUT
# ------------------------------------------------------------

INPUT = Path("Cartouche_C.text.svg")
OUTPUT = Path("import_pipeline.svg")


# ------------------------------------------------------------
# IMPORT
# ------------------------------------------------------------

print("=" * 60)
print("DEBUG IMPORT PIPELINE")
print("=" * 60)
print()

print("Reading:", INPUT)

paths = import_svg_paths(INPUT)

print(type(paths))
print("Number of paths:", len(paths))

for i, p in enumerate(paths[:5]):
    print()
    print("PATH", i)
    print("type =", type(p))
    print("segments =", len(p))
    print("empty =", p.is_empty)
    print("stroke =", p.stroke_enabled)
    print("fill =", p.fill_enabled)

    for obj in p:
        print("   ", type(obj))
        break

print()
print(f"VectorPaths imported : {len(paths)}")

segments = sum(len(p) for p in paths)

print(f"Total segments       : {segments}")

print()


# ------------------------------------------------------------
# BUILD DRAWING
# ------------------------------------------------------------

drawing = Drawing(
    name="DEBUG IMPORT",
    width=0,
    height=0,
)

drawing.paths = paths


# ------------------------------------------------------------
# EXPORT
# ------------------------------------------------------------

print("Writing:", OUTPUT)

write_debug_svg(
    drawing,
    OUTPUT,
)

print()
print("Finished.")
