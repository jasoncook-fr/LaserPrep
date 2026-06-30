# LaserPrep

LaserPrep is an open-source Python application for preparing student vector files for laser cutting.

The goal of the project is to automate the repetitive preflight work normally performed by a laser cutter operator before sending jobs to Inkscape and the laser driver.

Instead of manually inspecting dozens of PDF files every day, LaserPrep imports them, analyses their geometry, validates them against workshop rules, and prepares a clean SVG project ready for production.

---

## Goals

LaserPrep is designed around three principles:

- Preserve the student's artwork whenever possible.
- Detect and report problems before modifying anything.
- Apply only safe, deterministic corrections automatically.

The long-term objective is to provide a complete preflight pipeline for educational fabrication workshops.

---

## Current Features

### PDF Import

- Import one or more PDF files from a project folder
- Preserve vector geometry
- Support straight lines and Bézier curves
- Create one Inkscape layer per imported drawing

### Geometry Analysis

- Compute the true geometric bounds of each drawing
- Ignore empty page margins
- Report drawing dimensions
- Detect whether the drawing fits the available laser bed

### Automatic Positioning

- Place imported drawings at a configurable offset
- Keep all geometry inside the usable work area

### Automatic Rotation

- Rotate drawings 90° when required to fit the selected laser bed

### Machine Validation

Supports multiple laser bed sizes.

Current configuration:

- Large machine
- Small machine

Reports whether each drawing fits each machine.

### Geometry Diagnostics

Currently reports:

- Zero-length lines
- Tiny line segments
- Duplicate geometry
- Shortest detected segment
- Unsupported PDF primitives

### Geometry Cleanup

Currently implemented:

- Remove zero-length line segments

Duplicate detection has been implemented and validated.

Automatic duplicate removal is currently under redesign so that color and stroke information are preserved before cleanup decisions are made.

---

## Planned Features

### Color Analysis

- Detect all colors used
- Report unsupported colors
- Report laser-compatible colors

### Color Normalization

- Snap near colors to the official laser palette
- Convert imported colors automatically

### Stroke Normalization

- Display-friendly stroke widths inside Inkscape
- Automatic export using laser hairline widths

### Geometry Cleanup

- Duplicate removal
- Tiny segment removal
- Geometry simplification
- Additional CAD cleanup tools

### Production Reports

Generate operator-friendly reports showing:

- Geometry statistics
- Color usage
- Cleanup actions
- Machine compatibility
- Warnings

---

## Project Structure

```
LaserPrep/
│
├── main.py
├── config.py
├── drawing.py
├── geometry_cleanup.py
├── pdf_reader.py
├── project.py
├── svg_writer.py
│
└── ...
```

---

## Workflow

```
PDF Files
      │
      ▼
Import
      │
      ▼
Geometry Analysis
      │
      ▼
Geometry Cleanup
      │
      ▼
Color Analysis
      │
      ▼
Color Normalization
      │
      ▼
Stroke Normalization
      │
      ▼
SVG Export
      │
      ▼
Inkscape
      │
      ▼
Laser Cutter
```

---

## Current Status

LaserPrep is under active development.

The geometry engine is functional and currently includes:

- PDF vector import
- Geometry measurement
- Automatic positioning
- Automatic rotation
- Machine compatibility checking
- Geometry diagnostics
- Initial cleanup tools

The next development milestone focuses on color analysis and normalization before final production cleanup.

---

## Requirements

Python 3.11+

Main libraries:

- lxml
- pypdfium2
- tkinter (standard library)

---

## License

MIT License

---

## Author

Jason Cook

Franco-American visual artist and educator based in Montpellier, France.

LaserPrep was developed to streamline the preparation of student laser-cutting files in educational fabrication workshops while remaining completely open source.
