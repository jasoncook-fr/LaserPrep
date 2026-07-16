#!/usr/bin/env python3

"""
analyse_glyphs.py

Analyse every glyph (<symbol>) contained in a Poppler SVG.

The goal is to determine whether glyph geometry is stable
enough to build a glyph database.
"""

from pathlib import Path
import xml.etree.ElementTree as ET


SVG = Path(
    "TEST_FILES/quarantine/cart_C/BAMBU.text.svg"
)


def strip_namespace(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def count_commands(d):

    commands = {
        "M": 0,
        "L": 0,
        "C": 0,
        "Z": 0,
    }

    for c in d:
        if c in commands:
            commands[c] += 1

    return commands


def analyse_symbol(symbol):

    paths = symbol.findall(".//{*}path")

    total_paths = len(paths)

    total_M = 0
    total_L = 0
    total_C = 0
    total_Z = 0

    styles = set()

    for path in paths:

        d = path.attrib.get("d", "")

        counts = count_commands(d)

        total_M += counts["M"]
        total_L += counts["L"]
        total_C += counts["C"]
        total_Z += counts["Z"]

        style = path.attrib.get("style")

        if style:
            styles.add(style)

    return {
        "paths": total_paths,
        "M": total_M,
        "L": total_L,
        "C": total_C,
        "Z": total_Z,
        "styles": styles,
    }


def main():

    tree = ET.parse(SVG)
    root = tree.getroot()

    symbols = []

    for symbol in root.iter():

        if strip_namespace(symbol.tag) != "symbol":
            continue

        glyph_id = symbol.attrib.get("id", "<unknown>")

        info = analyse_symbol(symbol)

        symbols.append((glyph_id, info))

    print("=" * 80)
    print("GLYPH ANALYSIS")
    print("=" * 80)

    for glyph_id, info in symbols:

        print()

        print(glyph_id)
        print("-" * len(glyph_id))

        print(f"Paths   : {info['paths']}")
        print(f"M       : {info['M']}")
        print(f"L       : {info['L']}")
        print(f"C       : {info['C']}")
        print(f"Z       : {info['Z']}")

        if info["styles"]:
            print("Styles")

            for style in sorted(info["styles"]):
                print(f"    {style}")

    print()

    print("=" * 80)
    print(f"Total glyphs : {len(symbols)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
