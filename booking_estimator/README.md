# Booking Estimator (experimental)

An isolated experimental package for SVG analysis and future laser-runtime prediction.

## Current scope

- **Stage 1:** root SVG physical-dimension parsing and viewBox scale resolution.
- **Stage 2:** geometry records, points, bounding boxes, affine matrix composition, and SVG transform-list parsing.

The geometry foundation deliberately does not yet extract SVG elements or measure paths. Transform-list parsing currently supports `matrix`, `translate`, `scale`, `rotate` (including a center), `skewX`, and `skewY`, with argument validation and composition. Coordinates in future geometry analysis are intended to be normalized to millimetres. SVG matrix composition is defined so that `self.compose(other)` applies `other` first, then `self`.

Absolute SVG units are converted using the CSS SVG reference of 96 px per inch. Unitless root dimensions are treated as CSS px. If either physical root dimension is absent, physical dimensions are deliberately not inferred from the viewBox alone.

Aspect-ratio mismatches are flagged; full SVG preserveAspectRatio behavior is not yet implemented.

## Development

Run tests from the repository root:

```bash
python -m pytest -q booking_estimator/tests
```
