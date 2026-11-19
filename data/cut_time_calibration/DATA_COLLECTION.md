# Data collection and normalization

## Intake
Measurements can be supplied through different methods (SVG files and observed times, spreadsheet experiments, notes, or future structured forms). Intake method does not dictate the canonical schema.

## Normalize without losing context
- Preserve the original source file and source worksheet/test name.
- Assign a unique ID to each observation.
- Convert observed elapsed time to seconds, retaining original notation where ambiguous.
- Preserve reported units and geometry descriptions.
- Extract SVG geometry using the same LaserPrep measurement pipeline whenever possible.
- Capture machine, material, profile, speed and optimization settings.
- Keep Optim. Vectors and JcT Courbes separate. If only a combined label is available, preserve it and mark the individual setting as unknown rather than inferring.
- Distinguish controlled tests from production jobs.

## Quality levels
- **Verified**: source and relevant conditions clear; measurement and normalized values checked.
- **Provisional**: record usable but missing/uncertain metrics or settings.
- **Questionable**: ambiguity likely to affect interpretation; retain for audit, exclude from model fitting until resolved.
- **Rejected**: invalid or demonstrably corrupted data; retain audit trail but exclude.

## Modeling principles
- Analyze controlled tests to isolate factors (e.g. optimization, speed, machine, geometry, fill orientation).
- Use production data for real-world validation and refinement.
- Avoid confounding: paired tests should ideally use identical geometry, material, profile and machine while changing one factor.
- Do not extrapolate beyond collected conditions without flagging uncertainty.
- Keep train/validation separation by job or experiment series to avoid leakage from repeated or near-identical observations.
- Report prediction uncertainty and calibration coverage as the dataset grows.

## Ambiguous source data
Never guess ambiguous time formats, settings, units, or missing metrics. Keep original data and flag for clarification.
