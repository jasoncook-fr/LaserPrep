# LaserPrep

LaserPrep prepares student PDF files for laser cutting by converting them into a single, clean SVG suitable for inspection and production in Inkscape.

The project is designed to accept a wide variety of PDF files produced by CAD, vector illustration, and architectural software while automatically repairing many common problems before export.

---

## Features

* Import vector geometry from PDF
* Automatic page rotation when beneficial
* Geometry alignment
* Colour normalization
* Stroke width normalization
* Machine size validation
* Anchor point counting
* Duplicate geometry detection
* Hidden geometry detection
* Raster image detection
* Live text detection
* Automatic text outline extraction using Poppler
* Watermark detection and removal
* Artifact detection
* SVG export for Inkscape

---

## Processing Pipeline

```text
PDF
 │
 ├── Geometry Import
 │
 ├── Text Extraction
 │      │
 │      ├── Poppler
 │      ├── SVG Analysis
 │      ├── SVG Text Import
 │      ├── Text Group Analysis
 │      ├── Artifact Detection
 │      └── Watermark Removal
 │
 ├── Geometry Cleanup
 │
 ├── Colour Normalization
 │
 ├── Validation
 │
 └── SVG Export
```

---

## Project Structure

```
main.py
│
├── pdf_reader.py
├── text_import.py
├── geometry_cleanup.py
├── colour_normalization.py
├── svg_writer.py
│
├── drawing.py
├── vector_path.py
├── svg_path_parser.py
├── svg_transform.py
│
├── artifact_detector.py
├── watermark_detector.py
├── watermark_remover.py
├── text_group_analysis.py
│
└── diagnostics.py
```

Development and investigation scripts are located in the `tools/` directory and are not required for normal operation.

---

## Workflow

1. Read PDF
2. Import vector geometry
3. Extract text outlines
4. Remove watermark artifacts
5. Merge text and geometry
6. Clean geometry
7. Validate drawing
8. Export SVG

---

## Output

The generated SVG is intended to be opened in Inkscape, where each drawing can be visually inspected before being sent to the laser cutter.

---

## Design Philosophy

LaserPrep intentionally performs only a limited number of automatic repairs.

Whenever possible, original geometry is preserved. Automatic modifications are limited to operations that are deterministic and safe, such as:

* rotation
* alignment
* stroke normalization
* colour normalization
* text outline extraction
* watermark removal
* duplicate removal

This keeps the exported SVG predictable and suitable for manufacturing.

---

## Requirements

* Python 3.11+
* PyMuPDF
* Poppler (`pdftocairo`)
* Inkscape (for final inspection)

---

## Current Status

The PDF import pipeline is complete and supports:

* vector geometry
* direct SVG paths
* glyph-reference SVGs
* automatic text outline extraction
* artifact and watermark removal
* SVG export


