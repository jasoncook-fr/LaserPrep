# LaserPrep

LaserPrep is an open-source Python application for preparing vector PDF
artwork for laser cutting.

Developed for educational fabrication workshops, LaserPrep automates the
preflight process normally performed before importing files into
Inkscape and sending them to a laser cutter. It analyses vector artwork,
validates it against workshop rules, performs safe, deterministic
corrections, and generates a production-ready SVG project.

Unlike simple PDF converters, LaserPrep preserves the original vector
path structure of the source document. This allows artwork created in
applications such as Adobe Illustrator and Archicad to be reproduced
faithfully while providing a consistent analysis and validation
pipeline.

------------------------------------------------------------------------

# Philosophy

LaserPrep follows four core principles:

-   Preserve the original artwork whenever possible.
-   Analyse before modifying.
-   Apply only safe, deterministic corrections automatically.
-   Produce consistent, laser-ready SVG output regardless of the
    software that created the PDF.

------------------------------------------------------------------------

# Current Features

## PDF Import

-   Import one or more PDF files from a project folder.
-   Preserve the original vector path hierarchy.
-   Import straight lines and cubic Bézier curves.
-   Preserve drawing order.
-   Preserve continuous vector paths.
-   Create one Inkscape layer per imported drawing.

## Geometry Validation

-   True geometric bounds (ignoring page margins).
-   Automatic anchor/object counting.
-   Zero-length segment detection.
-   Tiny segment detection.
-   Duplicate geometry detection.
-   Unsupported PDF primitive reporting.
-   Machine size validation.

## Geometry Processing

-   Automatic 90° rotation when beneficial.
-   Automatic positioning on the laser bed.
-   Stroke width normalization.
-   Safe geometry cleanup.

## Colour Processing

-   Laser palette recognition.
-   Unsupported colour detection.
-   Colour normalization with configurable tolerance.
-   CMYK handling.
-   Black stroke detection.
-   Fill validation.

## Content Validation

-   Raster image detection.
-   Live text detection.
-   White/background object detection.
-   Clipping mask detection.
-   Hidden object detection.

## SVG Export

-   One SVG layer per imported PDF.
-   Preservation of original vector paths.
-   Optimised continuous SVG path generation.
-   Configurable display stroke width.
-   Laser hairline export.

## Reporting

LaserPrep generates a detailed report for every drawing, including
drawing dimensions, machine compatibility, geometry statistics, colour
usage, cleanup actions and automatic corrections.

------------------------------------------------------------------------

# Workflow

``` text
PDF → Validation → Cleanup → Colour Normalisation → Rotation & Positioning → SVG → Inkscape → Laser Cutter
```

------------------------------------------------------------------------

# Architecture

``` text
Project
└── Drawing
    └── VectorPath
        ├── Line
        └── Bezier
```

Preserving the original vector paths is a core design principle. Rather
than reconstructing chains from individual segments after import,
LaserPrep retains the structure already present in the PDF.

------------------------------------------------------------------------

# Planned Development

-   Path analysis (length, orientation, open/closed).
-   Expanded PDF compatibility testing.
-   Operator-friendly reports.
-   Internal code cleanup.
-   Future laser optimisation tools.

------------------------------------------------------------------------

# Requirements

Python 3.11+

Libraries:

-   PyMuPDF
-   lxml
-   tkinter

------------------------------------------------------------------------

# Current Status

LaserPrep now provides a complete preflight pipeline for vector
laser-cutting workflows. Development is focused on architectural
cleanup, broader compatibility testing and preparation for Version 1.0.

------------------------------------------------------------------------

# License

MIT License

------------------------------------------------------------------------

# Author

**Jason Cook**

Franco-American visual artist, educator and developer based in
Montpellier, France.
