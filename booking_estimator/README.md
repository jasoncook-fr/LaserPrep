# Booking Estimator (experimental)

An isolated experimental package for SVG analysis and future laser-runtime prediction.

## Current scope

- **Stage 1:** root SVG physical-dimension parsing and viewBox scale resolution.
- **Stage 2:** geometry records, points, bounding boxes, affine matrix composition, and SVG transform-list parsing.
- **Stage 3:** primitive extraction, group transforms, and inherited styles.
- **Stage 4:** SVG path data parsing for absolute and relative M/L/H/V/Z and cubic Bézier C/S commands, including smooth-control reflection.

Path parsing produces line and cubic Bézier segment records in SVG user coordinates. Quadratic curves and arcs remain unsupported. This stage does not yet calculate path length, bounds, normalize units, or classify laser operations.

The geometry foundation deliberately keeps extraction, normalization, measurement, and classification separate. Transform-list parsing currently supports matrix, translate, scale, rotate (including a center), skewX, and skewY. Coordinates in future geometry analysis are intended to be normalized to millimetres.

Absolute SVG units are converted using the CSS SVG reference of 96 px per inch. Unitless root dimensions are treated as CSS px. If either physical root dimension is absent, physical dimensions are deliberately not inferred from the viewBox alone. Aspect-ratio mismatches are flagged; full SVG preserveAspectRatio behavior is not yet implemented.

## Development

Run tests from the repository root:

```bash
python -m pytest -q booking_estimator/tests
```
