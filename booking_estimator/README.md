# Booking Estimator (experimental)

An isolated experimental package for SVG analysis and future laser-runtime prediction.

## Current scope

Stage 1 implements root SVG physical-dimension parsing and viewBox scale resolution. It does not yet extract geometry, apply transforms, classify operations, or predict runtime.

Absolute SVG units are converted using the CSS SVG reference of 96 px per inch. Unitless root dimensions are treated as CSS px. If either physical root dimension is absent, physical dimensions are deliberately not inferred from the viewBox alone.

Aspect-ratio mismatches are flagged; full SVG preserveAspectRatio behavior is not yet implemented.

## Development

Run the package tests from the repository root using the project's test environment:

```bash
pytest -q booking_estimator/tests
```
