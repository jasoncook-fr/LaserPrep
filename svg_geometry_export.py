"""
svg_geometry_export.py

LaserPrep Geometry Export

Exports the vector geometry of a MuPDF page to an SVG file.
This module does not parse or modify the SVG geometry. It only
asks MuPDF to generate it, with a small XML-safety cleanup to
prevent malformed source PDFs from producing invalid XML.
"""

from pathlib import Path


def _remove_invalid_xml_chars(text):
    """
    Remove characters that are forbidden in XML 1.0.

    Some PDFs can contain unusual control characters which MuPDF
    may carry into generated SVG attributes/text. ElementTree then
    fails with:

        ParseError: not well-formed (invalid token)

    This cleanup affects only illegal XML characters; it does not
    alter valid SVG geometry, coordinates, colors, or paths.
    """

    def valid_xml_char(ch):
        code = ord(ch)
        return (
            code in (0x9, 0xA, 0xD)
            or 0x20 <= code <= 0xD7FF
            or 0xE000 <= code <= 0xFFFD
            or 0x10000 <= code <= 0x10FFFF
        )

    return "".join(ch for ch in text if valid_xml_char(ch))


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

    # Defensive XML cleanup. This is only needed for malformed or
    # unusual source PDFs that cause MuPDF to emit illegal XML chars.
    svg = _remove_invalid_xml_chars(svg)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(svg, encoding="utf-8")

    return output_file
