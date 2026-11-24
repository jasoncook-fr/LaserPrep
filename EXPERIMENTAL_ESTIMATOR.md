# Experimental integrated estimator

Run from the repository root:

```bash
python3 integrated_time_estimator.py --machine 60W --cut-length-mm 13676 --vector-length-mm 6869 --fill-area-mm2 550 --overhead-sec 120
```

Inputs: machine, filled-engraving speed/scan condition, filled area, cut length,
combined vector-engraving length, JcT toggle for cut-rate selection, overhead
and provisional vector seconds-per-metre.

The cut rate is derived from controlled-series data whose distance values are
explicitly flagged as suspect. The vector rate is an adjustable provisional
placeholder. The fill component is regression-calibrated but has three points
per condition. This is a test harness and must not be treated as validated
whole-job predictions or integrated into production workflow yet.
