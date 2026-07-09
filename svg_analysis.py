"""
svg_analysis.py

LaserPrep
SVG Analysis

Version 1.1

Inspects a Poppler-generated SVG before import.

This module performs NO geometry import.
It simply analyses the SVG and classifies the type of
text representation so the correct importer can be chosen.
"""

from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET


# ============================================================
# Data class
# ============================================================

@dataclass
class SvgAnalysis:

    # --------------------------------------------------------
    # Document
    # --------------------------------------------------------

    path_count: int = 0

    # --------------------------------------------------------
    # Path types
    # --------------------------------------------------------

    direct_paths: int = 0
    transformed_paths: int = 0

    # --------------------------------------------------------
    # Geometry
    # --------------------------------------------------------

    bezier_paths: int = 0
    straight_paths: int = 0

    # --------------------------------------------------------
    # Glyphs
    # --------------------------------------------------------

    symbol_count: int = 0
    use_count: int = 0

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    has_direct_paths: bool = False
    has_glyphs: bool = False

    # --------------------------------------------------------
    # Import capabilities
    # --------------------------------------------------------

    text_possible: bool = False
    direct_import_possible: bool = False
    glyph_import_required: bool = False

    # --------------------------------------------------------
    # Overall classification
    # --------------------------------------------------------

    mode: str = "UNKNOWN"


# ============================================================
# Helpers
# ============================================================

def _strip(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


# ============================================================
# Analysis
# ============================================================

def analyze_svg(svg_filename) -> SvgAnalysis:

    tree = ET.parse(svg_filename)
    root = tree.getroot()

    info = SvgAnalysis()

    for node in root.iter():

        tag = _strip(node.tag)

        # ----------------------------------------------------
        # Glyph definitions
        # ----------------------------------------------------

        if tag == "symbol":
            info.symbol_count += 1
            continue

        if tag == "use":
            info.use_count += 1
            continue

        # ----------------------------------------------------
        # Paths
        # ----------------------------------------------------

        if tag != "path":
            continue

        info.path_count += 1

        d = node.attrib.get("d", "")

        if node.attrib.get("transform"):
            info.transformed_paths += 1
        else:
            info.direct_paths += 1

        if any(c in d for c in "CcQqSsAa"):
            info.bezier_paths += 1
        else:
            info.straight_paths += 1

    # ========================================================
    # Classification
    # ========================================================

    info.has_glyphs = (
        info.symbol_count > 0 and
        info.use_count > 0
    )

    info.has_direct_paths = (
        info.direct_paths > 0
    )

    # ========================================================
    # Import capabilities
    # ========================================================

    info.direct_import_possible = (
        info.direct_paths > 0
    )

    info.glyph_import_required = (
        info.symbol_count > 0 and
        info.use_count > 0
    )

    info.text_possible = (
        info.direct_import_possible or
        info.glyph_import_required
    )

    # ========================================================
    # Overall mode
    # ========================================================

    if info.has_glyphs and info.has_direct_paths:
        info.mode = "MIXED_PATHS"

    elif info.has_glyphs:
        info.mode = "GLYPH_REFERENCES"

    elif info.has_direct_paths:
        info.mode = "DIRECT_PATHS"

    else:
        info.mode = "UNKNOWN"

    return info


# ============================================================
# Report
# ============================================================

def print_svg_analysis(info: SvgAnalysis):

    print()
    print("=" * 60)
    print("SVG ANALYSIS")
    print("=" * 60)

    print()
    print("Paths")
    print("-------------------------------------")
    print(f"Total paths        : {info.path_count}")
    print(f"Direct paths       : {info.direct_paths}")
    print(f"Transformed paths  : {info.transformed_paths}")

    print()
    print("Geometry")
    print("-------------------------------------")
    print(f"Bezier paths       : {info.bezier_paths}")
    print(f"Straight paths     : {info.straight_paths}")

    print()
    print("Glyphs")
    print("-------------------------------------")
    print(f"Symbol definitions : {info.symbol_count}")
    print(f"Glyph references   : {info.use_count}")

    print()
    print("Import")
    print("-------------------------------------")
    print(f"Text detected      : {info.text_possible}")
    print(f"Direct import      : {info.direct_import_possible}")
    print(f"Glyph import       : {info.glyph_import_required}")

    print()
    print("Classification")
    print("-------------------------------------")

    print(f"Mode               : {info.mode}")
