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
        print(*args, **kwargs)

def _same_geometry(a, b, tolerance=0.10):
    """
    Return True when two vector paths represent the same geometry.

    Comparison is based on:
        - number of segments
        - segment types
        - segment coordinates
        - closed state

    A small tolerance allows for floating-point differences between
    the normal geometry import and the text import.
    """

    if getattr(a, "closed", False) != getattr(b, "closed", False):
        return False

    # Geometry alone is not enough to identify a duplicate.  In some PDFs,
    # the same artwork geometry is present in the normal import with a white
    # fill, while the text import correctly produces it as black.  Those are
    # visually different paths and the black path must be retained.
    if getattr(a, "fill_enabled", False) != getattr(b, "fill_enabled", False):
        return False
    if getattr(a, "fill_color", None) != getattr(b, "fill_color", None):
        return False

    a_objects = list(a)
    b_objects = list(b)

    if len(a_objects) != len(b_objects):
        return False

    def same_point(p1, p2):
        return (
            abs(p1.x - p2.x) <= tolerance
            and abs(p1.y - p2.y) <= tolerance
        )

    def same_segment(s1, s2):
        from drawing import Line, Bezier

        if type(s1) is not type(s2):
            return False

        if isinstance(s1, Line):
            return (
                same_point(s1.start, s2.start)
                and same_point(s1.end, s2.end)
            )

        if isinstance(s1, Bezier):
            return (
                same_point(s1.start, s2.start)
                and same_point(s1.control1, s2.control1)
                and same_point(s1.control2, s2.control2)
                and same_point(s1.end, s2.end)
            )

        return False

    return all(
        same_segment(s1, s2)
        for s1, s2 in zip(a_objects, b_objects)
    )

# ============================================================
# Public API
# ============================================================

def import_text(drawing, pdf_file):
    """
    Import all text outlines from a PDF and merge them into
    an existing Drawing.
    """

    pdf_file = Path(pdf_file)

    svg_file = diag.temp_folder / f"{pdf_file.stem}.text.svg"

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

    # GLYPH_REFERENCES use SVG <symbol>/<use> structures and are
    # handled elsewhere. DIRECT_PATHS, however, are already real
    # text outlines and must be imported normally.
    if analysis.mode == "GLYPH_REFERENCES":
        _dbg(f"Text import skipped for {analysis.mode}.")
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

    object_count = 0

    for path in text_paths:

        duplicate = any(
            _same_geometry(path, existing)
            for existing in drawing.paths
        )

        if duplicate:
            _dbg("Skipping imported text path already present in drawing.")
            continue

        # Imported text is already a complete SVG path.
        # Keep it separate from topology reconstruction.
        drawing.paths.append(path)

        # Do NOT add text primitives to drawing.objects.
        # This prevents topology from rebuilding stroked copies.

    _dbg(f"Imported objects : {object_count}")

    _dbg()
