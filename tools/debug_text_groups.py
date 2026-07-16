#!/usr/bin/env python3

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from poppler import text_to_paths
from svg_text_import import import_svg_paths


PDF = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "Cartouche_C.pdf"
)


def main():

    svg = PDF.with_suffix(".text.svg")

    print("=" * 70)
    print("PDF → SVG")
    print("=" * 70)

    text_to_paths(PDF, svg)

    print("=" * 70)
    print("SVG → VectorPaths")
    print("=" * 70)

    paths = import_svg_paths(svg)

    print(f"\nImported paths : {len(paths)}")

    groups = {}

    for p in paths:
        groups.setdefault(p.group_id, []).append(p)

    print()
    print("=" * 70)
    print("TEXT GROUPS")
    print("=" * 70)

    report = []

    for gid, plist in groups.items():

        left = min(p.bounds[0] for p in plist)
        top = min(p.bounds[1] for p in plist)
        right = max(p.bounds[2] for p in plist)
        bottom = max(p.bounds[3] for p in plist)

        width = right - left
        height = bottom - top
        area = width * height

        report.append(
            (
                area,
                gid,
                len(plist),
                width,
                height,
                (left + right) / 2,
                (top + bottom) / 2,
            )
        )

    #
    # Sort by area (smallest first).
    #
    report.sort()

    for area, gid, npaths, width, height, cx, cy in report:

        print(
            f"Group {gid:4d}"
            f"  paths={npaths:4d}"
            f"  area={area:10.2f}"
            f"  bbox={width:8.2f} × {height:8.2f}"
            f"  centre=({cx:8.2f}, {cy:8.2f})"
        )

    print()
    print(f"Temporary SVG kept at:\n{svg}")


if __name__ == "__main__":
    main()
