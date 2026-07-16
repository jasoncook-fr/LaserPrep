#!/usr/bin/env python3

"""
analyse_text_groups.py

Diagnostic tool for text group detection.
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
from text_group_analysis import group_text_paths


PDF = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "BAMBU.pdf"
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

    groups = group_text_paths(paths)

    print()
    print("=" * 80)
    print(f"Found {len(groups)} text groups")
    print("=" * 80)

    for number, group in enumerate(groups):

        print()
        print(f"Group {number}")
        print("-" * 40)

        print(f"Glyphs : {len(group.paths)}")

        if len(group.path_indices) <= 10:
            print(f"Paths  : {group.path_indices}")
        else:
            print(
                f"Paths  : "
                f"{group.path_indices[0]} ... {group.path_indices[-1]}"
            )

        print(
            f"Bounds : "
            f"({group.left:.2f}, {group.top:.2f}) - "
            f"({group.right:.2f}, {group.bottom:.2f})"
        )

        print(
            f"Size   : "
            f"{group.width:.2f} × {group.height:.2f} mm"
        )

        print(
            f"Centre : "
            f"({group.centre.x:.2f}, {group.centre.y:.2f})"
        )

    print()
    print("Analysis complete.")


if __name__ == "__main__":
    main()
