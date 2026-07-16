#!/usr/bin/env python3

"""
export_path_range.py

Export a range of imported VectorPaths to an SVG.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from poppler import text_to_paths
from svg_text_import import (
    import_svg_paths,
    get_svg_page_size,
)
from drawing import Drawing
from project import Project
from svg_writer import write_svg


# ============================================================
# Configuration
# ============================================================

PDF = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "BAMBU.pdf"
)

START = 0
COUNT = 50

OUTPUT = PROJECT_ROOT / "path_range.svg"


# ============================================================
# Main
# ============================================================

def main():

    svg = PDF.with_suffix(".text.svg")

    print("Converting PDF...")
    text_to_paths(PDF, svg)

    print("✓ Conversion successful")
    print()

    print("Importing paths...")
    paths = import_svg_paths(svg)

    page_width, page_height = get_svg_page_size(svg)

    print(f"Imported paths : {len(paths)}")

    end = min(START + COUNT, len(paths))
    selected = paths[START:end]

    print()
    print(f"Exporting paths {START} .. {end - 1}")
    print(f"Selected paths : {len(selected)}")

    project = Project("PathRange")

    drawing = Drawing(
        name="Imported",
        width=page_width,
        height=page_height,
    )

    project.add(drawing)

    for path in selected:

        #
        # Preserve the VectorPath.
        #
        drawing.paths.append(path)

        #
        # Preserve every segment.
        #
        for obj in path:
            drawing.add(obj)

    print()
    print(f"Objects : {len(drawing.objects)}")
    print(f"Paths   : {len(drawing.paths)}")

    print()
    print("Writing SVG...")

    write_svg(
        project,
        OUTPUT,
    )

    print()
    print(f"Exported : {OUTPUT}")


if __name__ == "__main__":
    main()
