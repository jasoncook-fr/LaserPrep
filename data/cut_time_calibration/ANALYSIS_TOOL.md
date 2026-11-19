# Calibration analysis script

Run from the LaserPrep repository root:

```bash
python3 analyse_cut_time_calibration.py
```

The script reads the calibration ledger CSVs and writes a Markdown report and optional plots to:

`data/cut_time_calibration/analysis_output/`

Matplotlib is optional. Without it, the statistical report is still generated. This is exploratory analysis; it does not modify the CSV ledger or integrate coefficients into LaserPrep.

See the generated report for data caveats and next experimental recommendations.
