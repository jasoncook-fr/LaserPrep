#!/usr/bin/env python3

"""
compare_glyphs.py

Compares two imported VectorPaths.

Used to understand why two visually identical glyphs may
produce different fingerprints.
"""

from pathlib import Path
import sys
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from poppler import text_to_paths
from svg_text_import import import_svg_paths
from glyph_fingerprint import (
    canonical_geometry,
    fingerprint,
)


PDF = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "BAMBU.pdf"
)


#
# Change these two indices when required.
#
A = 4
B = 21


def main():

    svg = PDF.with_suffix(".text.svg")

    text_to_paths(PDF, svg)

    paths = import_svg_paths(svg)

    path_a = paths[A]
    path_b = paths[B]

    print("=" * 80)
    print("GLYPH COMPARISON")
    print("=" * 80)

    print()
    print(f"Glyph A : {A}")
    print(f"Glyph B : {B}")

    print()
    print("Fingerprints")
    print("------------")

    fp_a = fingerprint(path_a)
    fp_b = fingerprint(path_b)

    print(fp_a)
    print(fp_b)

    print()

    if fp_a == fp_b:
        print("✓ Fingerprints identical")
    else:
        print("✗ Fingerprints differ")

    print()

    geo_a = canonical_geometry(path_a)
    geo_b = canonical_geometry(path_b)

    print("Canonical records")
    print("-----------------")

    print(f"A : {len(geo_a)}")
    print(f"B : {len(geo_b)}")

    print()

    same = True

    maximum = max(len(geo_a), len(geo_b))

    for i in range(maximum):

        rec_a = geo_a[i] if i < len(geo_a) else None
        rec_b = geo_b[i] if i < len(geo_b) else None

        if rec_a != rec_b:

            same = False

            print(f"Difference at record {i}")

            print("A")
            pprint(rec_a)

            print("B")
            pprint(rec_b)

            print()

    if same:

        print("Canonical geometry is identical.")

    print()

    print("=" * 80)


if __name__ == "__main__":
    main()
