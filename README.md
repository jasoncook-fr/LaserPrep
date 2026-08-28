# LaserPrep

LaserPrep is a Python application that prepares student PDF drawings for laser cutting.

It imports one or more PDF files from a project folder, automatically detects and repairs common issues, validates the result, and produces a single SVG ready for inspection and production in Inkscape.

The goal is to reduce manual preparation time while providing a reliable and repeatable workflow for digital fabrication laboratories and educational workshops.

---

# Version

**Current release:** v1.1

This release marks the first stable production version of the complete processing pipeline, including incremental batch processing.

---

# Features

* Batch processing of student project folders
* Incremental batch processing — unchanged projects are skipped
* Automatic detection of new, changed, or removed PDFs
* Automatic PDF import
* Vector geometry extraction
* Text outline extraction
* Watermark detection and removal
* Artifact detection
* Geometry cleanup and optimization
* Duplicate line removal
* Zero-length geometry removal
* Colour normalization
* Machine-size validation
* Complexity analysis
* Operator and developer reports
* SVG export for Inkscape

---

# Batch Processing

LaserPrep can process an entire batch of student folders automatically.

The configured `BATCH_ROOT` directory should contain one folder per student:

```text
BATCH_ROOT/
├── Student_A/
├── Student_B/
├── Student_C/
└── ...
```

Students may organize their files in either of two ways.

### PDFs directly in the student folder

Students who prefer a simple or temporary organization can place PDFs directly in their folder:

```text
Student_A/
├── drawing1.pdf
├── drawing2.pdf
└── drawing3.pdf
```

These PDFs are treated as a single project.

### Projects in subfolders

Students who have several projects can organize them into folders:

```text
Student_B/
├── Project_1/
│   ├── drawing1.pdf
│   └── drawing2.pdf
└── Project_2/
    ├── drawing1.pdf
    └── drawing2.pdf
```

Each immediate subfolder containing PDFs is treated as a separate project.

LaserPrep intentionally processes only this one level of project folders. Deeper folder structures are not scanned:

```text
Student_C/
└── Project_1/
    └── Versions/
        └── drawing.pdf
```

In this example, `Versions` will not be processed.

---

# Incremental Batch Processing

LaserPrep does not unnecessarily reprocess projects that have already been successfully processed.

For each project, LaserPrep records a SHA-256 fingerprint of every PDF in an administrator-controlled state file.

State files are stored outside the student/Nextcloud folders, under the configured `ADMIN_ROOT`:

```text
ADMIN/
└── STATE/
    ├── 008.json
    ├── 009.json
    ├── 009__testFolder.json
    └── ...
```

This keeps the processing state outside the student workspace so that students cannot modify or delete the information used to determine whether a project needs to be reprocessed.

For projects stored directly in a student folder, the state file uses the student folder name. For projects inside a project subfolder, the state filename combines the student and project names to avoid collisions.

On a subsequent batch run:

* If all PDFs are unchanged, the project is skipped.
* If a PDF is modified, the project is processed again.
* If a new PDF is added, the project is processed again.
* If a PDF is removed, the project is processed again.
* If processing fails, the new state is not recorded, so the project will be attempted again on the next batch run.

The comparison is based on the contents of the PDFs, not their filenames. Therefore, replacing a PDF with a revised version using the same filename will correctly trigger reprocessing.

All administrator-controlled batch data is kept under `ADMIN_ROOT`, separate from the student workspace:

```text
ADMIN/
├── CURRENT_BATCH_REPORT.txt
├── BATCH_REPORTS/
└── STATE/
```

The state files are internal administrative data and should not normally be edited manually.

---

# Batch Reports

Each Batch Mode run produces a batch report containing the important aborts and warnings generated during processing.

The most recent report is always available directly in the administrator folder:

```text
ADMIN/
└── CURRENT_BATCH_REPORT.txt
```

This file is replaced by each new Batch Mode run.

A permanent historical copy is also created for every run:

```text
ADMIN/
└── BATCH_REPORTS/
    ├── 2026-08-28_14-32-05.txt
    ├── 2026-08-28_17-06-41.txt
    └── ...
```

The timestamped reports are retained so that previous batch runs can be reviewed later.

---

# Processing Pipeline

```text
Project Folder
       │
       ▼
Check processing state
       │
       ├── Unchanged → Skip
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
       │
       ▼
Record successful processing state
```

---

# Project Structure

```text
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

* Python 3.11+
* PyMuPDF
* Poppler (`pdftocairo`)
* Inkscape

---

# Typical Workflow

### Individual project

1. Launch LaserPrep.
2. Select a project folder.
3. LaserPrep imports every PDF in the folder.
4. Geometry and text are repaired automatically.
5. Validation is performed.
6. Reports are generated.
7. A production-ready SVG is created.
8. Open the SVG in Inkscape.
9. Inspect each layer.
10. Send the job to the laser cutter.

### Batch processing

1. Place student folders inside `BATCH_ROOT`.
2. Students place PDFs directly in their folder or in one level of project subfolders.
3. Launch LaserPrep in Batch Mode.
4. LaserPrep identifies new or changed projects.
5. Unchanged projects are skipped.
6. Projects requiring processing are processed normally.
7. Successfully processed projects are recorded in the administrator-controlled state directory.
8. A current batch report is written to `ADMIN/CURRENT_BATCH_REPORT.txt`.
9. A timestamped copy of the batch report is saved in `ADMIN/BATCH_REPORTS/`.
10. Open the resulting SVGs in Inkscape for inspection.
11. Send approved jobs to the laser cutter.

---

# Current Status

LaserPrep v1.1 is the current production release.

The complete processing pipeline has been implemented, including PDF import, text outlining, geometry cleanup, colour normalization, validation, reporting, SVG generation, and incremental batch processing.

Future development will focus on:

* performance improvements
* internal refactoring
* workflow enhancements
* maintainability

while preserving compatibility with the current production pipeline.

---

# License

MIT License
