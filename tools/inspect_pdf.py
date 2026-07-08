#!/usr/bin/env python3

import sys
import fitz
from collections import Counter


def inspect_pdf(filename):
    doc = fitz.open(filename)

    print("=" * 70)
    print(filename)
    print("=" * 70)

    total_drawings = 0
    primitive_counter = Counter()

    for page_number, page in enumerate(doc):

        print(f"\nPAGE {page_number + 1}")
        print("-" * 70)

        drawings = page.get_drawings()

        print(f"Drawing objects : {len(drawings)}")

        total_drawings += len(drawings)

        for index, drawing in enumerate(drawings):

            print()
            print("=" * 50)
            print(f"DRAWING {index + 1}")
            print("=" * 50)

            #print(f"Stroke : {drawing.get('color')}")

            print("Keys")

            for key in sorted(drawing.keys()):
                print(f"   {key} : {drawing[key]}")

            print(f"Fill   : {drawing.get('fill')}")
            print(f"Width  : {drawing.get('width')}")
            print(f"Closed : {drawing.get('closePath')}")
            print(f"Items  : {len(drawing['items'])}")

            commands = Counter()

            for item in drawing["items"]:
                cmd = item[0]
                commands[cmd] += 1
                primitive_counter[cmd] += 1

            print("\nPrimitive counts")

            for cmd in sorted(commands):
                print(f"   {cmd:>3} : {commands[cmd]}")

            print("\nFirst primitives")

            for i, item in enumerate(drawing["items"][:10]):
                print(f"{i+1:2d}: {item}")
    print("\n")
    print("=" * 70)
    print("GLOBAL SUMMARY")
    print("=" * 70)

    print(f"Drawing objects : {total_drawings}")

    print()

    for cmd in sorted(primitive_counter):
        print(f"{cmd:>3} : {primitive_counter[cmd]}")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage:")
        print("    python inspect_pdf.py drawing.pdf")
        sys.exit()

    inspect_pdf(sys.argv[1])
