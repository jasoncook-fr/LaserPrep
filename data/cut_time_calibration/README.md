# Laser cut-time calibration dataset

This directory contains the persistent data and documentation for developing a measured, validated cut-time estimator for the LaserPrep workflow.

## Dataset types
- **Controlled tests**: structured experiments that isolate machine behavior, geometry, speed, fill direction, or optimization settings.
- **Production jobs**: real SVG jobs with observed machine time and LaserPrep-extracted geometry metrics.

These sources are complementary and must remain identifiable; do not merge them into an undifferentiated pool.

## Files
- `README.md`: overview and rules.
- `DATA_DICTIONARY.md`: fields and definitions.
- `DATA_COLLECTION.md`: collection, normalization and quality rules.
- `production_jobs_master.csv`: canonical production-job dataset.
- `controlled_tests_master.csv`: canonical controlled-test dataset.
- `raw/`: source spreadsheets and files, when available and committed.

## Data rules
1. Raw source files are preserved; normalized data never replaces them.
2. Actual elapsed times are ground truth. Do not substitute model estimates.
3. Unknown values remain blank—not zero.
4. Each record has a unique ID and provenance.
5. Optimization options are independent: **Optim. Vectors** and **JcT Courbes** must be recorded separately where possible, for both 60W and 100W.
6. Keep settings (machine, profile, material, speed, optimization, fill direction) with the observation.
7. Do not count copied, repeated, or derived values as independent observations without explicit repeat metadata.
8. Controlled tests and production jobs are analyzed separately where appropriate, then combined only where model design justifies it.
9. Preserve provisional and quality flags; don't silently promote uncertain records to verified.
10. Record schema changes in this documentation and update ingestion tools/tests as applicable.

## Current status
The calibration effort is in the data collection and validation stage. No prediction model is considered validated yet. Dataset completeness and source quality vary.

