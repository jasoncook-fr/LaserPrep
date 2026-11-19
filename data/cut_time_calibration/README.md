# Laser Cut Time Calibration Dataset

This directory is the persistent calibration ledger for developing a practical cutting-time estimator for the LaserPrep workflow and the 60W and 100W CO2 laser cutters.

## Dataset streams

- **Production jobs**: real SVG jobs with measured runtime and LaserPrep geometry metrics when available. Stored in `production_jobs_master.csv`.
- **Controlled tests**: deliberately designed tests used to isolate machine/settings/geometry effects. Stored in `controlled_tests_master.csv`.

Both streams are useful, but they are not interchangeable. Keep source, test context, uncertainty and original observations. Do not combine them blindly or count duplicate observations as independent samples.

## Data handling principles

1. Preserve measured times as ground truth; don't replace them with calculated values.
2. Never silently infer missing fields; blanks mean unknown/not captured.
3. Record machine (60W/100W), material, profile and profile adjustments where known.
4. Record **Optim. Vectors** and **JcT Courbes** independently as ON/OFF/unknown.
5. Keep controlled and production observations distinguishable.
6. Keep provisional records marked until geometry and metadata are verified.
7. Maintain raw source files separately when possible; normalized CSVs are working data, not a replacement for source evidence.
8. Assign stable unique IDs: `JOB-####` for production and `CAL-####` for controlled tests.
9. Schema changes should be documented and backward-compatible where practical.
10. Model development must include validation against withheld real jobs, not only fitting to calibration tests.

## Files

- `production_jobs_master.csv`
- `controlled_tests_master.csv`
- `README.md`
- `DATA_DICTIONARY.md`
- `DATA_COLLECTION.md`
- `SCHEMA_EVOLUTION.md`

## Workflow for new observations

When new data arrives, inspect existing records, normalize it, assign the next ID, preserve provenance and uncertainties, update this repository, and summarize what changed. Periodically audit inconsistencies and validate estimates against actual jobs.

## Current limitations

Some production records are incomplete. Several jobs remain provisional pending geometry or metadata extraction. Some controlled tests contain limited experimental context (e.g. fill orientation details or time formatting ambiguity in the source workbook); retain these limitations in analysis rather than treating them as resolved.

## Paired production observation (2026-11-19)

JOB-0014 (100W, 28:53) and JOB-0015 (60W, 26:00) record the same LaGesse SVG geometry, using CB-1.5 and both optimization options ON. Geometry was verified identical: 16,950.816 mm blue straight cutting and 43,210.096 mm green vector engraving; 549 paths total (28 blue, 521 green). These actual durations are ground truth. Subtracting provisional straight-cut estimates (~356.8 s for 100W and ~358.5 s for 60W) leaves residuals of ~1,376.2 s and ~1,201.5 s respectively. Those residuals include engraving and machine/job overhead and must not be treated as measured engraving-only times or generalized coefficients. Source SVGs are referenced by filename; the files themselves were analyzed in-session.
