# Booking Estimator (experimental)

An isolated experimental package for SVG analysis and future laser-runtime prediction.

## Current scope

- **Stage 1:** root SVG physical-dimension parsing and viewBox scale resolution.
- **Stage 2:** geometry records, points, bounding boxes, affine matrix composition, and SVG transform-list parsing.
- **Stage 3:** primitive extraction, group transforms, and inherited styles.
- **Stage 4:** SVG path data parsing for absolute and relative M/L/H/V/Z, cubic Bézier C/S, and quadratic Bézier Q/T commands, including smooth-control reflection, and elliptical arc A/a commands.

Path parsing produces line, cubic, and quadratic Bézier segment records in SVG user coordinates. Elliptical arcs are represented as arc records with radii, rotation, flags, and endpoints; arc-length measurement and conversion remain deferred. This stage does not yet calculate path length, bounds, normalize units, or classify laser operations.

The geometry foundation deliberately keeps extraction, normalization, measurement, and classification separate. Transform-list parsing currently supports matrix, translate, scale, rotate (including a center), skewX, and skewY. Coordinates in future geometry analysis are intended to be normalized to millimetres.

Absolute SVG units are converted using the CSS SVG reference of 96 px per inch. Unitless root dimensions are treated as CSS px. If either physical root dimension is absent, physical dimensions are deliberately not inferred from the viewBox alone. Aspect-ratio mismatches are flagged; full SVG preserveAspectRatio behavior is not yet implemented.

## Development

Run tests from the repository root:

```bash
python -m pytest -q booking_estimator/tests
```


## Segment length measurement (Stage 8, partial)

The `lengths` module measures line segments exactly and quadratic/cubic Bézier curves numerically using adaptive Simpson integration of the parametric speed. `path_length()` sums supported segments. Elliptical arc measurement is deliberately deferred to a subsequent increment. Results remain in the coordinate units of the parsed segments (conversion to millimetres comes later).
