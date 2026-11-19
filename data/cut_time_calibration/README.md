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

Some production records are incomplete. Two recent 100W jobs are marked provisional pending extraction of detailed geometry. Some controlled tests contain limited experimental context (e.g. fill orientation details or time formatting ambiguity in the source workbook); retain these limitations in analysis rather than treating them as resolved.