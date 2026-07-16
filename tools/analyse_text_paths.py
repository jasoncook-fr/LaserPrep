#!/usr/bin/env python3

"""
analyse_text_paths.py

Diagnostic tool for LaserPrep.

Imports a PDF, extracts imported text paths and prints
their geometric properties.

Used to identify unwanted text such as watermarks,
printer marks and other PDF artifacts.
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

PDF = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "Cartouche_B.pdf"
)


def main():

    svg = PDF.with_suffix(".text.svg")

    print("=" * 80)
    print("PDF → SVG")
    print("=" * 80)

    text_to_paths(PDF, svg)

    page_width, page_height = get_svg_page_size(svg)

    print()
    print(f"Page size : {page_width:.2f} × {page_height:.2f} mm")

    paths = import_svg_paths(svg)

    print(f"Imported paths : {len(paths)}")

    #
    # Keep only imported text.
    #
    text_paths = []

    for index, path in enumerate(paths):

        if getattr(path, "is_text", False):
            text_paths.append((index, path))

    print(f"Text paths : {len(text_paths)}")

    #
    # Largest text first.
    #
    text_paths.sort(
        key=lambda item: item[1].width * item[1].height,
        reverse=True,
    )

    print()
    print("=" * 120)
    print(
        f"{'Path':>6} "
        f"{'Area':>10} "
        f"{'Width':>10} "
        f"{'Height':>10} "
        f"{'Objects':>8} "
        f"{'Centre X':>10} "
        f"{'Centre Y':>10}"
    )
    print("=" * 120)

    for index, path in text_paths:

        area = path.width * path.height

        print(
            f"{index:6d} "
            f"{area:10.2f} "
            f"{path.width:10.2f} "
            f"{path.height:10.2f} "
            f"{path.object_count:8d} "
            f"{path.center.x:10.2f} "
            f"{path.center.y:10.2f}"
        )

    print()
    print("Analysis complete.")


if __name__ == "__main__":
    main()
