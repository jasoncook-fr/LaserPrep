"""
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
    Text Group Analysis
      ↓
    Watermark Detection
      ↓
    Watermark Removal
      ↓
    Drawing

Version 1.2
"""

from pathlib import Path

DEBUG = False

from svg_analysis import analyze_svg
from poppler import text_to_paths
from svg_text_import import (
    import_svg_paths,
    get_svg_page_size,
)
from pdf_text import extract_pdf_text
from text_group_analysis import group_text_paths
from artifact_detector import find_artifact_groups
from watermark_remover import remove_watermarks

from diagnostics import diag
from debug_svg_writer import write_imported_paths


def _dbg(*args, **kwargs):
    if DEBUG:
        _dbg(*args, **kwargs)


# ============================================================
# Public API
# ============================================================

def import_text(drawing, pdf_file):
    """
    Import all text outlines from a PDF and merge them into
    an existing Drawing.
    """

    pdf_file = Path(pdf_file)

    svg_file = pdf_file.with_suffix(".text.svg")

    # --------------------------------------------------------
    # PDF -> SVG
    # --------------------------------------------------------
    # --------------------------------------------------------
    # PDF semantic text
    # --------------------------------------------------------

    spans = extract_pdf_text(pdf_file)

    _dbg()
    _dbg("PDF text")
    _dbg("--------")

    for span in spans:
        _dbg(f"{span.text} ({span.font}, {span.size:.1f} pt)")

    _dbg()
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

    if analysis.mode == "GLYPH_REFERENCES":
        _dbg("Glyph-based text detected.")
        _dbg("Skipping text import.")
        return

    # --------------------------------------------------------
    # SVG -> VectorPaths
    # --------------------------------------------------------

    text_paths = import_svg_paths(svg_file)

    page_width, page_height = get_svg_page_size(svg_file)

    _dbg(f"Imported text paths : {len(text_paths)}")

    debug_svg = (
        diag.debug_folder
        / f"{pdf_file.stem}.imported_text.svg"
    )

    write_imported_paths(
        text_paths,
        debug_svg,
    )

    # --------------------------------------------------------
    # Watermark detection
    # --------------------------------------------------------

    text_groups = group_text_paths(text_paths)

    artifact_groups = find_artifact_groups(
        text_groups,
        drawing.width,
        drawing.height,
    )

    _dbg()
    _dbg("Artifact candidates")
    _dbg("--------------------")

    for group in artifact_groups:
        _dbg(
            f"Glyphs={len(group.paths)} "
            f"Size={group.width:.2f} x {group.height:.2f}"
        )

    _dbg(f"Detected groups: {len(artifact_groups)}")
    _dbg()

    for i, group in enumerate(artifact_groups):

        direct = sum(
            getattr(p, "is_direct_text", False)
            for p in group.paths
        )

        _dbg(
            f"Artifact {i}: "
            f"glyphs={len(group.paths)} "
            f"direct={direct} "
            f"size={group.width:.2f} x {group.height:.2f}"
        )


    if artifact_groups:

        _dbg(
            f"Detected artifact groups : "
            f"{len(artifact_groups)}"
        )

        for group in artifact_groups:

                _dbg(
                    f"Removing watermark group: "
                    f"{len(group.paths)} glyphs | "
                    f"{group.width:.2f} × {group.height:.2f} mm | "
                    f"Bounds=({group.left:.2f}, {group.top:.2f}) "
                    f"({group.right:.2f}, {group.bottom:.2f})"
                )

        text_paths = remove_watermarks(
            text_paths,
            artifact_groups,
        )

        _dbg(
            f"Remaining text paths : "
            f"{len(text_paths)}"
        )

    else:

        _dbg("No artifacts detected.")

    # --------------------------------------------------------
    # Merge into Drawing
    # --------------------------------------------------------
    for path in text_paths:
        left, top, right, bottom = path.bounds

        if left < 20 and bottom > page_height - 5:
            _dbg(
                f"WARNING: path at ({left:.2f}, {top:.2f}) "
                f"({right:.2f}, {bottom:.2f})"
            )

    _dbg(f"Merging {len(text_paths)} text paths...")

    object_count = 0

    for path in text_paths:

        drawing.paths.append(path)

        for obj in path:
            drawing.add(obj)
            object_count += 1

    _dbg(f"Imported objects : {object_count}")

    _dbg()



