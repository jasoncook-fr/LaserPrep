# LaserPrep

LaserPrep is a Python application that prepares student PDF drawings for laser cutting.

It imports PDF files from a project folder, automatically repairs common problems, and produces a single SVG ready for inspection and production in Inkscape.

The goal is to make laser cutting more reliable while reducing manual preparation time for workshop staff.

---

# Version

Current release: **v1.0**

This release marks the completion of the first stable processing pipeline.

---

# Features

- Batch processing of project folders
- Automatic PDF import
- Vector geometry extraction
- Text outline extraction
- Glyph-reference SVG support
- Watermark detection and removal
- Artifact detection
- Geometry cleanup
- Duplicate line removal
- Zero-length geometry removal
- Colour normalization
- Geometry statistics
- Processing diagnostics
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
├── diagnostics.py

Debug
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
2. Select the folder containing student PDF files.
3. LaserPrep imports every PDF.
4. Geometry and text are repaired automatically.
5. A single SVG is generated.
6. Open the SVG in Inkscape.
7. Inspect each layer.
8. Send to the laser cutter.

---

# Current Status

Version 1.0 provides a complete production pipeline for preparing laser-cutting jobs.

Future development will focus primarily on:

- internal architecture
- code cleanup
- performance improvements
- additional diagnostics
- improved maintainability

rather than major changes to the processing pipeline.

---

# License

MIT License
