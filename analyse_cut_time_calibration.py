#!/usr/bin/env python3
"""Offline analysis of LaserPrep cut-time calibration CSVs.

Run from repository root:
    python3 analyse_cut_time_calibration.py

Outputs Markdown analysis and optional Matplotlib plots in
data/cut_time_calibration/analysis_output/. This is exploratory analysis only;
it does not modify calibration data or production estimator code.
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "cut_time_calibration"
OUT = DATA / "analysis_output"
CONTROLLED = DATA / "controlled_tests_master.csv"
PRODUCTION = DATA / "production_jobs_master.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def linear_fit(x, y):
    """OLS line y = slope*x + intercept, plus R²; returns None for degenerate data."""
    n = len(x)
    if n < 2:
        return None
    xm, ym = sum(x) / n, sum(y) / n
    ssx = sum((v - xm) ** 2 for v in x)
    if ssx == 0:
        return None
    slope = sum((a - xm) * (b - ym) for a, b in zip(x, y)) / ssx
    intercept = ym - slope * xm
    sst = sum((v - ym) ** 2 for v in y)
    ssr = sum((b - (slope * a + intercept)) ** 2 for a, b in zip(x, y))
    r2 = 1 - ssr / sst if sst else float("nan")
    return slope, intercept, r2


def parse_fill_area(geometry):
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm", geometry, re.I)
    return float(m.group(1)) * float(m.group(2)) if m else None


def parse_distance(geometry):
    m = re.search(r"reported distance\s+(\d+(?:\.\d+)?)\s*mm", geometry, re.I)
    return float(m.group(1)) if m else None


def parse_spline_fraction(geometry):
    m = re.search(r"spline fraction\s+([\d.]+)", geometry, re.I)
    return float(m.group(1)) if m else None


def safe_float(v):
    try:
        return float(v) if v not in (None, "") else None
    except (ValueError, TypeError):
        return None


def fmt(v, digits=3):
    return f"{v:.{digits}f}" if v is not None and math.isfinite(v) else "n/a"


def analyse_fill(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("measurement_type") != "filled engraving":
            continue
        area = parse_fill_area(row.get("geometry", ""))
        t = safe_float(row.get("actual_time_seconds"))
        if area is None or t is None:
            continue
        key = (row.get("machine", ""), row.get("test_group", ""), row.get("optimization", ""))
        groups[key].append((area, t, row.get("record_id", "")))

    fits = {}
    for key, observations in groups.items():
        fit = linear_fit([o[0] for o in observations], [o[1] for o in observations])
        if fit:
            fits[key] = (fit, observations)
    return fits


def analyse_cut(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("measurement_type") != "mixed line/spline cut":
            continue
        distance = parse_distance(row.get("geometry", ""))
        spline = parse_spline_fraction(row.get("geometry", ""))
        t = safe_float(row.get("actual_time_seconds"))
        if distance is None or spline is None or t is None:
            continue
        key = (row.get("machine", ""), row.get("optimization", ""), row.get("test_group", ""))
        groups[key].append((distance, spline, t, row.get("record_id", "")))
    return groups


def make_plots(fill_fits, cut_groups):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    OUT.mkdir(parents=True, exist_ok=True)

    # Filled-engraving plots: one figure, grouped series by machine/speed/scan.
    for machine in ("60W", "100W"):
        fig, ax = plt.subplots()
        plotted = False
        for key, (fit, obs) in fill_fits.items():
            if key[0] != machine:
                continue
            (slope, intercept, r2), _ = fit, obs
            label = f"{key[1]} / {key[2]} (R²={r2:.3f})"
            xs = [a for a, _, _ in obs]
            ys = [t for _, t, _ in obs]
            ax.scatter(xs, ys, label=label)
            line_x = [min(xs), max(xs)]
            ax.plot(line_x, [slope*x + intercept for x in line_x])
            plotted = True
        if plotted:
            ax.set_title(f"Filled engraving calibration — {machine}")
            ax.set_xlabel("Area (mm²)")
            ax.set_ylabel("Runtime (seconds)")
            ax.legend(fontsize="small")
            ax.grid(True, alpha=0.25)
            fig.tight_layout()
            fig.savefig(OUT / f"filled_{machine}.png", dpi=160)
        plt.close(fig)

    # Mixed cut test plots, time against nominal distance, series separately.
    for machine in ("60W", "100W"):
        fig, ax = plt.subplots()
        plotted = False
        for key, obs in cut_groups.items():
            if key[0] != machine:
                continue
            xs = [d for d, _, _, _ in obs]
            ys = [t for _, _, t, _ in obs]
            ax.plot(xs, ys, marker="o", label=f"{key[1]} / {key[2]}")
            plotted = True
        if plotted:
            ax.set_title(f"Mixed line/spline test series — {machine}")
            ax.set_xlabel("Reported distance (mm; source flagged as problematic)")
            ax.set_ylabel("Runtime (seconds)")
            ax.legend(fontsize="small")
            ax.grid(True, alpha=0.25)
            fig.tight_layout()
            fig.savefig(OUT / f"mixed_cut_{machine}.png", dpi=160)
        plt.close(fig)
    return True


def build_report(controlled, production, fill_fits, cut_groups, plots_available):
    OUT.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Calibration analysis (exploratory)",
        "",
        "Generated by `analyse_cut_time_calibration.py`. No source data was modified.",
        "",
        "## Scope and cautions",
        "",
        "- Controlled tests and production jobs are analyzed separately.",
        "- The mixed line/spline distance series is source-documented as problematic ('bad-distance series'); regressions below are descriptive, not reliable rate calibration.",
        "- Filled engraving fits use three area points per condition. Fit intercepts are extrapolations, not independently measured startup overhead.",
        "- The dataset does not identify scan-line interval, fill orientation details, profile settings, or all machine overheads consistently.",
        "- This report is not a production runtime prediction and does not establish validated estimator coefficients.",
        "",
        f"Controlled records: **{len(controlled)}**; production records: **{len(production)}**.",
        "",
        "## Filled engraving: linear fits",
        "",
        "OLS fit: runtime = slope × area + intercept. Coefficient is shown as seconds per 1,000 mm².",
        "",
        "| Machine | Test group (speed) | Scan | s/1,000 mm² | Intercept (s) | R² |",
        "|---|---|---|---:|---:|---:|",
    ]
    for key, (fit, obs) in sorted(fill_fits.items()):
        slope, intercept, r2 = fit
        machine, speed, scan = key
        lines.append(f"| {machine} | {speed} | {scan} | {fmt(slope*1000)} | {fmt(intercept,2)} | {fmt(r2,4)} |")
    lines.extend(["", "### Filled engraving interpretation", "",
        "- Compare the fitted slopes across speed and scan direction; the dataset suggests strong, near-proportional effects.",
        "- Treat the intercept as a fit artifact/possible small-job overhead proxy until replicated with additional sizes, especially smaller areas.",
        "- Three points per condition are insufficient to characterize nonlinearities or uncertainty robustly.",
        "",
        "## Mixed line/spline tests (descriptive only)", "",
        "| Machine | Condition | Test group | Slope (s/mm) | Intercept (s) | R² |",
        "|---|---|---|---:|---:|---:|"])
    for key, obs in sorted(cut_groups.items()):
        fit = linear_fit([o[0] for o in obs], [o[2] for o in obs])
        if fit:
            slope, intercept, r2 = fit
            lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {fmt(slope,6)} | {fmt(intercept,2)} | {fmt(r2,4)} |")
    lines.extend(["", "These regressions confound nominal distance and spline fraction, and source notes flag distance reliability. They must not be interpreted as isolated line/spline rates or optimization multipliers.", "",
        "## Production data audit", "",
        "| Job | Machine | Runtime (s) | Geometry fields populated | Notes |",
        "|---|---|---:|---|---|"])
    for row in production:
        populated = [k for k in ("blue_cut_straight_mm","blue_cut_curves_mm","green_vector_mm","red_vector_mm","black_fill_area_mm2") if row.get(k)]
        note = (row.get("notes") or row.get("operator_notes") or "").replace("|", "\\|")
        lines.append(f"| {row.get('job_id')} | {row.get('machine')} | {row.get('actual_time_seconds')} | {', '.join(populated) or 'none'} | {note} |")
    lines.extend(["", "### Paired LaGesse jobs", "",
        "JOB-0014 and JOB-0015 are recorded as same geometry, 16,950.816 mm blue straight cut plus 43,210.096 mm green vector engraving, both optimization options ON, and different machines. Their measured total runtimes are 1,733 s (100W) and 1,560 s (60W).",
        "",
        "These are a useful paired production comparison, but the existing notes' residuals after provisional cutting subtraction are not measured engraving-only times. Do not use these two jobs to independently validate and fit the same coefficients.",
        "",
        "## Additional recent production observations", "",
        "JOB-0016 and JOB-0017 were added from two SVG production files measured on 2026-11-20. Path counts and profile/optimization notes are captured in the ledger; geometry length/area metrics remain pending and these records are not used to fit controlled coefficients.",
        "",
        "## Plot output", "",
        ("Matplotlib plots generated in this directory." if plots_available else "Matplotlib was not available; plots skipped. Install Matplotlib to enable plots."),
        "",
        "- `filled_60W.png` and `filled_100W.png`",
        "- `mixed_cut_60W.png` and `mixed_cut_100W.png`",
        "",
        "## Recommended next experiments", "",
        "1. Repeat filled engraving tests (at least 2–3 repeats per condition) and add intermediate/smaller areas to test fixed overhead and linearity.",
        "2. Record scan-line interval, exact profile, speed/power settings, raster/fill strategy, material, and timing start/stop definition.",
        "3. Re-run the mixed cut test with verified geometry lengths and independent straight-only / spline-only conditions, with replicates.",
        "4. Use production jobs as holdout validation, not indiscriminate training data.",
        ""])
    (OUT / "analysis_report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    controlled = read_csv(CONTROLLED)
    production = read_csv(PRODUCTION)
    fill_fits = analyse_fill(controlled)
    cut_groups = analyse_cut(controlled)
    plots = make_plots(fill_fits, cut_groups)
    build_report(controlled, production, fill_fits, cut_groups, plots)
    print(f"Analysis complete: {OUT}")
    print(f"Report: {OUT / 'analysis_report.md'}")
    if plots:
        print("Plots generated (Matplotlib available).")
    else:
        print("Plots skipped (Matplotlib unavailable).")


if __name__ == "__main__":
    main()
