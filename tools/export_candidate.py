#!/usr/bin/env python3

"""
export_candidate.py

Export a single imported VectorPath to an SVG for inspection.
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
from svg_writer import write_debug_svg


PDF = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "Cartouche_B.pdf"
)

#
# Change this number to inspect another path.
#
PATH_INDICES = [
    287,
    288,
    289,
    290,
    291,
    292,
    293,
    294,
    295,
    296,
    297,
    298,
    299,
    300,
    301,
    302,
    303,
    304,
    305,
    306,
]

def main():

    svg = PDF.with_suffix(".text.svg")

    print("Converting PDF...")
    text_to_paths(PDF, svg)

    page_width, page_height = get_svg_page_size(svg)

    print("Importing paths...")
    paths = import_svg_paths(svg)
    print(f"Imported {len(paths)} paths")

    for index in PATH_INDICES:

        if index >= len(paths):
            print(f"Invalid path index {index}")
            return

    drawing = Drawing(
        name="CandidateCluster",
        width=page_width,
        height=page_height,
        paths=[paths[i] for i in PATH_INDICES],
    )

    outfile = PROJECT_ROOT / "candidate_cluster.svg"

    write_debug_svg(drawing, outfile)

    print()
    print(f"Exported: {outfile}")


if __name__ == "__main__":
    main()


