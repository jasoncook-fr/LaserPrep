#!/usr/bin/env python3
"""Experimental cut-time estimator using the filled-engraving calibration data.

This is deliberately separate from LaserPrep production processing. It currently
estimates filled engraving only. Vector-cut and other operation rates are not
sufficiently isolated in the calibration dataset to estimate reliably.

Example:
    python3 cut_time_estimator.py --machine 60W --speed 100 --scan Normal --area-mm2 4500
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "cut_time_calibration" / "controlled_tests_master.csv"


def area_from_geometry(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm", text, re.I)
    return float(match.group(1)) * float(match.group(2)) if match else None


def fit(x: list[float], y: list[float]):
    if len(x) < 2 or len(set(x)) < 2:
        raise ValueError("At least two distinct calibration areas are required.")
    n = len(x)
    xm, ym = sum(x) / n, sum(y) / n
    ssx = sum((a - xm) ** 2 for a in x)
    slope = sum((a - xm) * (b - ym) for a, b in zip(x, y)) / ssx
    intercept = ym - slope * xm
    sst = sum((b - ym) ** 2 for b in y)
    sse = sum((b - (slope * a + intercept)) ** 2 for a, b in zip(x, y))
    r2 = 1 - sse / sst if sst else float("nan")
    return slope, intercept, r2


def calibration(machine: str, speed: str, scan: str):
    rows = []
    with DATA.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("measurement_type") != "filled engraving":
                continue
            if row.get("machine") != machine or row.get("test_group") != speed or row.get("optimization") != scan:
                continue
            area = area_from_geometry(row.get("geometry", ""))
            try:
                seconds = float(row["actual_time_seconds"])
            except (KeyError, ValueError):
                continue
            if area is not None:
                rows.append((area, seconds, row.get("record_id", "")))
    if len(rows) < 2:
        raise ValueError(f"No usable calibration series found for {machine}, {speed}, {scan}.")
    slope, intercept, r2 = fit([r[0] for r in rows], [r[1] for r in rows])
    return rows, slope, intercept, r2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine", choices=("60W", "100W"), required=True)
    parser.add_argument("--speed", choices=("100%", "50%"), required=True)
    parser.add_argument("--scan", choices=("Normal", "Left-to-right"), required=True)
    parser.add_argument("--area-mm2", type=float, required=True, help="Total filled-engraving area in mm²")
    args = parser.parse_args()

    speed_group = f"Filled test {args.speed} speed"
    rows, slope, intercept, r2 = calibration(args.machine, speed_group, args.scan)
    estimate = slope * args.area_mm2 + intercept

    print("\nEXPERIMENTAL FILLED-ENGRAVING ESTIMATE")
    print("=" * 42)
    print(f"Machine:       {args.machine}")
    print(f"Speed:         {args.speed}")
    print(f"Scan:          {args.scan}")
    print(f"Area:          {args.area_mm2:,.1f} mm²")
    print(f"Calibration:   {len(rows)} observations ({', '.join(r[2] for r in rows)})")
    print(f"Fit:           {slope * 1000:.3f} s per 1,000 mm² + {intercept:.2f} s intercept")
    print(f"R²:            {r2:.4f}")
    print("-" * 42)
    print(f"ESTIMATED TIME: {estimate:.1f} seconds ({estimate / 60:.2f} minutes)")
    print("\nLimitations:")
    print("- Filled engraving only; vector cutting/engraving and machine overhead not included.")
    print("- Fit uses only three calibration sizes per condition.")
    print("- Intercept is extrapolated and is not independently measured overhead.")
    print("- Treat this as an experimental estimate, not a validated prediction.")


if __name__ == "__main__":
    main()
