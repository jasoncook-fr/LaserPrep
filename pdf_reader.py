"""
pdf_reader.py

LaserPrep PDF Reader
New MuPDF SVG geometry pipeline.
"""

from pathlib import Path
import fitz
from time import perf_counter

from drawing import Drawing

from svg_geometry_export import export_geometry_svg
from svg_geometry_import import import_svg_geometry
from diagnostics import diag

PT_TO_MM = 25.4 / 72.0


def read_pdf(filename: Path, clipping_removed=None) -> Drawing:
    total_start = perf_counter()
    doc = fitz.open(filename)
    page = doc[0]

    drawing = Drawing(
        name=filename.stem,
        width=page.rect.width * PT_TO_MM,
        height=page.rect.height * PT_TO_MM,
    )

    # Export page geometry as SVG using MuPDF
    export_start = perf_counter()
    svg_file = export_geometry_svg(
        page,
        output_file=diag.debug_folder / f"{filename.stem}.geometry.svg",
    )
    export_seconds = perf_counter() - export_start

    # Import geometry back into LaserPrep
    import_start = perf_counter()
    drawing.paths = import_svg_geometry(
        svg_file,
        page_width=drawing.width,
        page_height=drawing.height,
        clipping_removed=clipping_removed,
    )
    import_seconds = perf_counter() - import_start

    # Populate drawing.objects from imported paths
    drawing.objects.clear()
    for path in drawing.paths:
        drawing.objects.extend(path.objects)

    drawing.pdf_drawing_count = len(drawing.paths)
    drawing.pdf_statistics = {
        "paths": len(drawing.paths),
        "objects": len(drawing.objects),
        "unsupported": {},
    }

    svg_mb = svg_file.stat().st_size / (1024 * 1024)
    print(
        f"  TIMING {filename.name}: SVG export {export_seconds:.2f}s; "
        f"geometry import {import_seconds:.2f}s; total {perf_counter() - total_start:.2f}s; "
        f"SVG {svg_mb:.1f} MB; paths {len(drawing.paths):,}; objects {len(drawing.objects):,}"
    )

    with fitz.open(filename) as doc:
        page = doc[0]
    return drawing
