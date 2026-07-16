#!/usr/bin/env python3

"""
inspect_svg_metadata.py

Inspect every XML element and attribute contained in a
Poppler-generated SVG.

Used to determine whether metadata survives the PDF→SVG
conversion (IDs, labels, classes, accessibility tags, etc.).
"""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


SVG = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "BAMBU.text.svg"
)


def strip_namespace(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def main():

    tree = ET.parse(SVG)
    root = tree.getroot()

    counts = {}

    print("=" * 80)
    print("SVG METADATA INSPECTION")
    print("=" * 80)

    for element in root.iter():

        tag = strip_namespace(element.tag)

        counts[tag] = counts.get(tag, 0) + 1

        print()
        print("=" * 60)
        print(tag.upper())
        print("=" * 60)

        if element.attrib:

            for name, value in sorted(element.attrib.items()):

                print(f"{name} = {value}")

        else:

            print("(no attributes)")

        if element.text:

            text = element.text.strip()

            if text:

                print(f"text = {text}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for tag in sorted(counts):

        print(f"{tag:<15} {counts[tag]}")


if __name__ == "__main__":
    main()
