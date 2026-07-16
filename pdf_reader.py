"""
pdf_reader.py

LaserPrep PDF Reader
New MuPDF SVG geometry pipeline.
"""

from pathlib import Path
import fitz

from drawing import Drawing

from svg_geometry_export import export_geometry_svg
from svg_geometry_import import import_svg_geometry

PT_TO_MM = 25.4 / 72.0


def read_pdf(filename: Path) -> Drawing:
    doc = fitz.open(filename)
    page = doc[0]

    drawing = Drawing(
        name=filename.stem,
        width=page.rect.width * PT_TO_MM,
        height=page.rect.height * PT_TO_MM,
    )

    # Export page geometry as SVG using MuPDF
    svg_file = export_geometry_svg(
        page,
        filename.with_suffix(".geometry.svg")
    )

    # Import geometry back into LaserPrep
    drawing.paths = import_svg_geometry(svg_file)

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

    with fitz.open(filename) as doc:
        page = doc[0]
    return drawing
