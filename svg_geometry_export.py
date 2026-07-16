"""
svg_geometry_export.py

LaserPrep Geometry Export

Exports the vector geometry of a MuPDF page to an SVG file.
This module does not parse or modify the SVG. It simply asks
MuPDF to generate it.
"""

from pathlib import Path


def export_geometry_svg(page, output_file):
    """
    Export one PDF page as SVG.

    Parameters
    ----------
    page : fitz.Page
        MuPDF page object.

    output_file : str | Path
        Destination SVG filename.

    Returns
    -------
    Path
        Path to the generated SVG file.
    """

    output_file = Path(output_file)

    svg = page.get_svg_image()

    output_file.write_text(svg, encoding="utf-8")

    return output_file
