# LaserPrep

**LaserPrep** is a Python tool for preparing student vector drawings for laser cutting.

Its primary purpose is to automate the preparation of PDF submissions by converting them into clean SVG files that can be opened directly in Inkscape and sent to an Epilog laser cutter.

---

# Current Status

**Development Branch:** `text-import`

This branch introduces the first complete implementation of **PDF text recovery**.

Instead of losing text during PDF import, LaserPrep now reconstructs text as editable vector geometry by combining PyMuPDF and Poppler.

---

# Features

## PDF Geometry Import

Geometry is extracted directly from the PDF using **PyMuPDF**.

Supported primitives:

- Lines
- Cubic Bézier curves
- Closed paths
- Stroke colours
- Stroke widths

Geometry is preserved as native LaserPrep objects.

---

## SVG Text Import (NEW)

Text is recovered using a dedicated pipeline:

```
PDF
    │
    ▼
pdftocairo (Poppler)
    │
    ▼
SVG
    │
    ▼
SVG Path Parser
    │
    ▼
SVG Transform
    │
    ▼
Glyph Resolver
    │
    ▼
VectorPath
```

Implemented features:

- SVG path parsing
- Cubic Bézier support
- Compound SVG paths
- SVG transform matrices
- `<symbol>` glyph library
- `<use>` resolution
- Filled glyph rendering
- Even-odd fill support

Fonts are reconstructed as true vector geometry.

---

# Current Architecture

```
main.py
│
├── pdf_reader.py
│      │
│      ├── PyMuPDF geometry import
│      └── Text import pipeline
│
├── text_import.py
│      │
│      ├── Poppler conversion
│      ├── SVG parsing
│      └── Drawing merge
│
├── svg_path_parser.py
├── svg_transform.py
├── svg_text_import.py
│
└── svg_writer.py
```

---

# Design Philosophy

LaserPrep keeps PDF geometry and text recovery separate.

Geometry is read directly from the PDF using PyMuPDF.

Text is reconstructed from Poppler-generated SVG.

This avoids the limitations of either library alone.

---

# Current Limitations

Some CAD-generated PDFs (observed with Archicad educational exports) contain page elements that are **not exported by `pdftocairo -svg`**.

Examples include:

- title block text
- decorative graphics
- logos
- title block ornaments

In these files, Poppler exports only the educational watermark.

Since those objects never appear in the generated SVG, LaserPrep cannot currently recover them.

This appears to be related to the internal PDF structure rather than the LaserPrep importer.

Investigation is ongoing.

---

# Roadmap

## Completed

- ✔ PDF geometry import
- ✔ Colour preservation
- ✔ Bézier support
- ✔ Geometry analysis
- ✔ Duplicate removal
- ✔ SVG export
- ✔ Text recovery
- ✔ Compound glyph support
- ✔ Filled glyph rendering

## In Progress

- Investigation of Archicad title block objects
- Robust handling of additional PDF object types
- Improved error reporting
- Project cleanup and refactoring

---

# Dependencies

Python 3.11+

Libraries:

- PyMuPDF
- lxml
- Poppler (`pdftocairo`)
- tkinter (folder selection)

---

# License

MIT License
