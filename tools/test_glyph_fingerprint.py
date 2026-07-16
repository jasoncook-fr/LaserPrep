#!/usr/bin/env python3

"""
test_glyph_fingerprint.py

Compute fingerprints for every imported text glyph.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from poppler import text_to_paths
from svg_text_import import import_svg_paths
from glyph_fingerprint import fingerprint


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

    print()
    print("Importing glyphs...")

    paths = import_svg_paths(svg)

    print(f"Imported paths : {len(paths)}")

    print()
    print("=" * 80)
    print("FINGERPRINTS")
    print("=" * 80)

    seen = {}

    for index, path in enumerate(paths):

        fp = fingerprint(path)

        duplicate = fp in seen

        if duplicate:
            previous = seen[fp]
        else:
            seen[fp] = index
            previous = "-"

        print(
            f"{index:4d}   "
            f"{fp}   "
            f"duplicate={previous}"
        )

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"Glyphs            : {len(paths)}")
    print(f"Unique fingerprints : {len(seen)}")
    print(f"Duplicate glyphs    : {len(paths)-len(seen)}")


if __name__ == "__main__":
    main()
