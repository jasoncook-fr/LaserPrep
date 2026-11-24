# Cut-Time Estimator Data/Model Audit (2026-11-24)

## Scope
Reviewed calibration README/protocol/dictionary/schema notes, controlled_tests_master.csv (49 rows), production_jobs_master.csv (18 rows), analysis_report.md, geometry_summary.csv (14 specimen rows), cut_time_estimator.py, estimate_svg_cut_time.py, experimental-estimation README/ledger/prototype, and LCF analysis artifacts/inventory.

## Reconciliation
- Controlled tests: 49 records. CAL-0021–0032 and CAL-0038–0049 are 24 fill observations (3 nominal area points per each of 8 machine/speed/scan conditions). Use these for the fill regressions; only three points per condition and fill orientation/interval/material/profile context is incomplete.
- CAL-0001–0020 and CAL-0033–0037: 25 mixed line/spline observations from source-flagged bad-distance series. Descriptive only; not isolated rates or JcT multipliers.
- Production: 18 jobs. Many early records only have time/path count. JOB-0014/0015 are paired identical geometry (16,950.816 mm blue straight; 43,210.096 mm green; 549 paths) and paired actual times, but residual after provisional cut subtraction is not isolated engraving time. JOB-0016 geometry was PDF-derived and its blue length category was not proven straight-only. JOB-0017 raw SVG measurements include black stroke/fill geometry noted outside dedicated ledger fields. JOB-0018 raw-SVG approximate lengths with caveats.
- Geometry summary: 14 specimen rows; repeated geometry is present (10m24s/FONTAINE and 4m58s/17m52s, 26m00s/28m53s pairs). These should not count as independent geometry samples, although machine/runtime comparisons remain separate observations.
- Experimental benchmarks: BENCH-0001–0003 are pooled-length estimate comparisons; BENCH-0004 runtime only, geometry pending; BENCH-0005/0006 identical black-fill-only geometry, but vector optimization differs (ON vs OFF), JcT unknown and area pending. Some may overlap production/specimen sources; cross-ledger fingerprint reconciliation remains.
- LCF profiles: 37 files / 39 sections (22 iLASER-4000, 17 iLASER-4000_S-100W). Array semantics remain unverified; no unknown slots used as coefficients.

## Script audit
- cut_time_estimator.py: evidence-based fill-only regression from selected controlled condition, but manual area input; three points/condition and intercept limitations.
- estimate_svg_cut_time.py: combined hard-coded model, limited SVG command support (M/L/H/V/C/Z), cubic sampling, weak handling of transforms, units, fill topology/holes, strokes and arbitrary SVG complexity. Fill coefficients are a single selected condition rather than user choice; vector rates not independently validated.
- experimental_estimation/estimate_cut_time.py: historical isolated pooled-rate prototype, BENCH-0001 geometry hard-coded, dependency on geometry_summary.csv that is not committed as a portable input.

## Model policy
1. Fill estimate: fit from actual 3-point controlled condition selected by machine, nominal speed and scan direction.
2. Vector/cut geometry: show lengths and a provisional subtotal only using legacy hard-coded exploratory rates; explicitly flag as low confidence. Audit does not endorse those rates as validated.
3. Exclude bad-distance mixed series from coefficients.
4. Paired/repeated geometry and overlapping ledgers require duplicate awareness; avoid fitting and validation on the same observation.
5. LCF values not applied as multipliers until semantics validated.
6. Keep estimator tooling isolated from production.

## Known issues / next research
- Extract fill area from exact BENCH-0005/0006 files.
- Fingerprint/deduplicate across ledgers.
- Confirm scan interval, orientation, speed/power/material/profile and timing convention for controlled fill tests.
- Re-extract selected production geometry from final LaserPrep SVGs.
- Reserve independent holdouts before tuning.
