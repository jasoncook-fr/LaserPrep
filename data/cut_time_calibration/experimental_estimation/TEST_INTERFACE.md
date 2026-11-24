# Experimental SVG Estimator Test Interface

Research-only interface, isolated from LaserPrep production pipeline.

## Run
From the repository root:
```bash
python3 data/cut_time_calibration/experimental_estimation/test_svg_estimator.py path/to/file.svg --machine 60W --fill-speed 100% --scan Normal
```
Optional:
- `--optimization ON|OFF|UNKNOWN` records the selected context in the report; it does not change rates.
- `--save-report report.txt` saves the output.

## Model components
- Filled area: OLS regression dynamically fitted from the selected machine / speed / scan condition in `controlled_tests_master.csv` (3 calibration observations per condition).
- Blue cut, vector/stroke subtotal: provisional exploratory legacy rates from `estimate_svg_cut_time.py`; these are not validated independently. They are displayed separately from fill and explicitly caveated.

## Known limitations
- SVG geometry parsing supports only M/L/H/V/C/Z path commands; unsupported commands generate warnings and may lead to incomplete geometry.
- Transforms, arbitrary SVG units/viewBox scaling, fill rules/holes, non-black fills, stroke widths, and some SVG semantics are not resolved. Area/length calculations may be inaccurate for transformed or complex SVGs.
- The area estimator uses approximate polygon area; cubic Béziers are flattened by sampling.
- The fill model represents the selected controlled test condition; fill scan interval/orientation and other context are incomplete in source.
- OPT/JcT/material/profile settings do not modify rates.
- The combined estimate is experimental and should not be used as a promise, production decision, rejection threshold, or integration into LaserPrep.

Review `MODEL_DATA_AUDIT.md` for evidence reconciliation and model status.
