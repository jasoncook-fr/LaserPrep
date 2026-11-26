# Booking Estimator (experimental)

An isolated experimental package for SVG analysis and future laser-runtime prediction.

## Current scope

- **Stage 1:** root SVG physical-dimension parsing and viewBox scale resolution.
- **Stage 2:** geometry records, points, bounding boxes, affine matrix composition, and SVG transform-list parsing.
- **Stage 3:** primitive extraction, group transforms, and inherited styles.
- **Stage 4:** SVG path data parsing for absolute and relative M/L/H/V/Z, cubic Bézier C/S, and quadratic Bézier Q/T commands, including smooth-control reflection, and elliptical arc A/a commands.

Path parsing produces line, cubic, quadratic Bézier, and elliptical arc segment records in SVG user coordinates. Length measurement is implemented for all four segment types. Geometry bounds, millimetre normalization, and laser-operation classification remain future work.

The geometry foundation deliberately keeps extraction, normalization, measurement, and classification separate. Transform-list parsing currently supports matrix, translate, scale, rotate (including a center), skewX, and skewY. Coordinates in future geometry analysis are intended to be normalized to millimetres.

Absolute SVG units are converted using the CSS SVG reference of 96 px per inch. Unitless root dimensions are treated as CSS px. If either physical root dimension is absent, physical dimensions are deliberately not inferred from the viewBox alone. Aspect-ratio mismatches are flagged; full SVG preserveAspectRatio behavior is not yet implemented.

## Development

Run tests from the repository root:

```bash
python -m pytest -q booking_estimator/tests
```


## Segment length measurement (Stage 8, partial)

The `lengths` module measures line segments exactly and quadratic/cubic Bézier curves and elliptical arcs numerically using adaptive Simpson integration of parametric speed. SVG elliptical arcs are converted from endpoint form to center/angular form, including radii correction. `path_length()` sums supported segments. Results remain in the coordinate units of the parsed segments (conversion to millimetres comes later).


## Geometry transformation pipeline (Stage 9.1)

The `geometry_pipeline` module provides affine vector transformation, matrix determinant and inverse, and transformed line, quadratic, and cubic Bézier records. Elliptical arcs are preserved in an explicit transformed-arc wrapper rather than rewritten into potentially incorrect ellipse parameters under arbitrary affine transforms. SVG hierarchy integration and millimetre normalization remain subsequent stages.



## SVG hierarchy transform integration (Stage 9.2)

The `svg_transform_integration` module exposes `extract_transformed_paths()`.
It extracts SVG path records and applies the composed transforms inherited from
nested groups and path elements to line and Bézier segments. Arc records are
retained as explicit transformed-arc wrappers. Styles and source IDs remain
available. Primitive conversion, root viewport/viewBox normalization, and
millimetre conversion are still separate stages.


## SVG viewport normalization (Stage 9.3)

The `viewport` module maps SVG viewBox coordinates into physical viewport millimetres and implements `preserveAspectRatio`: `none`, all nine alignment positions, and `meet`/`slice` (including the default xMidYMid meet and optional defer token). This mapping is an explicit matrix; integration into full geometry processing and unit conversion follows in Stage 9.4.
