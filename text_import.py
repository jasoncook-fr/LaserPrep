"""
text_import.py

LaserPrep

Imports text geometry from a PDF by:

    PDF
      ↓
    Poppler
      ↓
    SVG
      ↓
    SVG Path Import
      ↓
    Drawing

Version 1.0
"""

from pathlib import Path
from svg_analysis import analyze_svg
from poppler import text_to_paths
from svg_text_import import import_svg_paths
from diagnostics import diag
from debug_svg_writer import write_imported_paths

# ============================================================
# Public API
# ============================================================

def import_text(drawing, pdf_file):
    """
    Import all text outlines from a PDF and merge them into
    an existing Drawing.

    Parameters
    ----------
    drawing : Drawing
        Existing drawing.

    pdf_file : Path
        Original PDF filename.
    """

    pdf_file = Path(pdf_file)

    svg_file = pdf_file.with_suffix(".text.svg")

    print()
    print("=" * 60)
    print("TEXT IMPORT")
    print("=" * 60)

    # --------------------------------------------------------
    # PDF -> SVG
    # --------------------------------------------------------

    text_to_paths(
        pdf_file,
        svg_file,
    )

    diag.export_file(
        svg_file,
        f"{pdf_file.stem}.text.svg",
    )

    # --------------------------------------------------------
    # Analyse SVG
    # --------------------------------------------------------

    analysis = analyze_svg(svg_file)

    print(f"SVG mode : {analysis.mode}")

    if analysis.mode == "GLYPH_REFERENCES":
        print("Glyph-based text detected.")
        print("Skipping text import.")
        return

    # --------------------------------------------------------
    # SVG -> VectorPaths
    # --------------------------------------------------------

    text_paths = import_svg_paths(svg_file)

    debug_svg = (
        diag.debug_folder
        / f"{pdf_file.stem}.imported_text.svg"
    )

    write_imported_paths(
        text_paths,
        debug_svg,
    )

    print(f"Merging {len(text_paths)} text paths...")

    object_count = 0

    for path in text_paths:

        drawing.paths.append(path)

        # VectorPath implements __iter__()
        for obj in path:

            drawing.add(obj)

            object_count += 1

    print(f"Imported objects : {object_count}")

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    try:
        #svg_file.unlink()

        print("Temporary SVG removed.")

    except Exception:

        print("Temporary SVG kept.")

    print()
