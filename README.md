# LaserPrep

LaserPrep is a Python application that prepares student PDF drawings for laser cutting.

It imports one or more PDF files from a project folder, automatically detects and repairs common issues, validates the result, and produces a single SVG ready for inspection and production in Inkscape.

The goal is to reduce manual preparation time while providing a reliable and repeatable workflow for digital fabrication laboratories and educational workshops.

---

# Version

**Current release:** v1.1

This release marks the first stable production version of the complete processing pipeline.

---

# Features

- Batch processing of project folders
- Automatic PDF import
- Vector geometry extraction
- Text outline extraction
- Watermark detection and removal
- Artifact detection
- Geometry cleanup and optimization
- Duplicate line removal
- Zero-length geometry removal
- Colour normalization
- Machine-size validation
- Complexity analysis
- Operator and developer reports
- SVG export for Inkscape

---

# Processing Pipeline

```
Project Folder
       │
       ▼
Read every PDF
       │
       ▼
Import vector geometry
       │
       ▼
Extract text outlines
       │
       ▼
Merge geometry
       │
       ▼
Remove watermark artifacts
       │
       ▼
Geometry cleanup
       │
       ▼
Colour normalization
       │
       ▼
Validation
       │
       ▼
Generate reports
       │
       ▼
Export project SVG
```

---

# Project Structure

```
main.py

Core
├── pdf_reader.py
├── project.py
├── drawing.py
├── svg_writer.py

Geometry
├── geometry_cleanup.py
├── geometry_statistics.py
├── geometry_chains.py
├── vector_path.py
├── svg_path_parser.py
├── svg_transform.py

Text
├── text_import.py
├── text_group_analysis.py
├── artifact_detector.py
├── watermark_detector.py
├── watermark_remover.py

Validation
├── colour_normalization.py
├── color_analysis.py
├── complexity.py

Reports
├── report.py
├── report_dev.py
├── batch_alerts.py

Diagnostics
├── diagnostics.py
├── debug_manager.py

Configuration
├── config.py
```

---

# Requirements

- Python 3.11+
- PyMuPDF
- Poppler (`pdftocairo`)
- Inkscape

---

# Typical Workflow

1. Launch LaserPrep.
2. Select the folder containing one or more student projects.
3. LaserPrep imports every PDF.
4. Geometry and text are repaired automatically.
5. Validation is performed.
6. Reports are generated.
7. A production-ready SVG is created.
8. Open the SVG in Inkscape.
9. Inspect each layer.
10. Send the job to the laser cutter.

---

# Current Status

LaserPrep v1.0 is the first production-ready release.

The complete processing pipeline has been implemented, including PDF import, text outlining, geometry cleanup, colour normalization, validation, reporting, and SVG generation.

Future development will focus on:

- performance improvements
- internal refactoring
- workflow enhancements
- maintainability

while preserving compatibility with the current production pipeline.

---

# License

MIT License
