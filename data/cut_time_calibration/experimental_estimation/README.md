# Experimental Time Estimation — Benchmarks and Usage

## Purpose and status
This is an isolated research experiment intended to produce a rough runtime estimate from the final LaserPrep SVG geometry. It is **not production code**, is not currently integrated into the LaserPrep processing/rejection workflow, and its estimates must not be used as authoritative machine-time promises or rejection decisions.

## Benchmark #001 (2026-11-20)
- Machine: 60W
- Optimization: Optim. Vectors ON; JcT Courbes ON (as recorded for the test)
- Profile: CB-2mm
- Final LaserPrep geometry: 71,219.862 mm total categorized stroked length (blue cut 18,787.697 mm; green vector 38,511.993 mm; black stroke 13,920.172 mm)
- SVG path elements: 3,491
- Estimate: 1,436 seconds (23m56s)
- Actual machine runtime: 1,785 seconds (29m45s)
- Error: +349 seconds; +24.3% underestimate relative to actual
- Implied actual effective rate: 39.90 mm/s
- Estimate effective rate: 49.58 mm/s

Geometry totals were validated with a second independent parser for this SVG. Filled-area engraving was not included in the initial model. The estimate used a pooled 60W OPT_ON rate from only two historical observations, so this is an early sanity check, not a validated model.

## Current prototype model
The first prototype is deliberately simple:
`estimated seconds = total categorized stroked length (mm) / pooled effective rate (mm/s)`
The prototype groups historical specimens by machine and explicit optimization marker in the specimen filename, then pools length and runtime for the group. For the first comparison, it used 60W / OPT_ON. Filenames lacking an explicit OPT marker are treated as UNKNOWN, not guessed. The experimental script currently has Benchmark #001 geometry hard-coded and is a prototype; make it accept arbitrary geometry before considering operational integration.

## Files
- `benchmark_results.csv`: benchmark validation ledger; record predicted and actual time, inputs and provenance here. It is distinct from controlled calibration and production job ledgers.
- `estimate_cut_time.py`: isolated prototype rate calculation / Benchmark #001 estimate.
- `README.md`: this protocol and benchmark summary.

## How to resume
1. Check out `feature/calibration-analysis` and inspect the working tree; preserve local changes.
2. Review `benchmark_results.csv` and this document first.
3. Benchmark another representative SVG by obtaining the final LaserPrep SVG geometry, recording geometry totals and metadata, and comparing the prediction with actual runtime when available.
4. Do not alter the existing controlled-test or production-job ledgers with benchmark validation observations unless their data definitions and provenance justify a separate, explicitly reviewed entry.
5. Before implementing a rejection/alert threshold, build a small sample of validation benchmarks, include a large-file test, and document limitations/false-positive risk.
6. Keep the estimator experimental and isolated from production until explicitly reviewed.

## Current next step
Test the estimator on a large final LaserPrep SVG that is believed to take hours, without sending that file to the machine. The immediate goal is to see whether the estimate can flag a job as potentially impractical. Then improve the script to accept an arbitrary SVG or geometry summary instead of the hard-coded benchmark geometry.

## Caveats
- Samples are few and conditions are heterogeneous.
- Effective rates conflate cutting, vector movement/engraving, travel, path ordering, acceleration, job overhead, profile, material and other factors.
- OPT_ON/OFF metadata may be incomplete in legacy filenames.
- Filled engraving area is not yet modeled in this prototype.
- A simple length/rate model can be inaccurate; benchmark validation is required.
- Do not silently update coefficients from a single benchmark.


### Prototype dependency / portability note
The prototype currently reads `data/cut_time_calibration/analysis_output/geometry_extraction/geometry_summary.csv`, a locally generated analysis file that is **not committed on this branch**. It will therefore not run on a fresh checkout unless that analysis CSV is generated or copied into place. The script is retained to document the calculation used during this experiment, not as a portable ready-to-run tool. A next development task is to make the estimator consume a user-specified SVG and extract geometry itself (using the experimental extractor), or otherwise formalize and commit a reproducible input dataset.
