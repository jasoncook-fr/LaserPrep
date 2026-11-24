#!/usr/bin/env python3
"""Exploratory analysis of LaserPrep controlled cut-time calibration tests.

This script reports descriptive comparisons only. It deliberately does not
produce deployable estimator coefficients or combine controlled data with
production observations.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "controlled_tests_master.csv"


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def number(pattern: str, text: str):
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None


def parse_mixed(row):
    text = row.get("geometry", "")
    line_fraction = number(r"line fraction\s*([0-9.]+)", text)
    spline_fraction = number(r"spline fraction\s*([0-9.]+)", text)
    distance = number(r"reported distance\s*([0-9.]+)\s*mm", text)
    time = float(row["actual_time_seconds"])
    if distance is None or line_fraction is None or spline_fraction is None:
        return None
    return {
        "id": row["record_id"], "machine": row["machine"],
        "optimization": row["optimization"], "group": row["test_group"],
        "distance": distance, "line_fraction": line_fraction,
        "spline_fraction": spline_fraction, "time": time,
        "seconds_per_m": time / (distance / 1000.0),
    }


def parse_fill(row):
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm", row.get("geometry", ""), re.I)
    if not m:
        return None
    a, b = map(float, m.groups())
    length, width = max(a, b), min(a, b)
    time = float(row["actual_time_seconds"])
    speed = "50%" if "50%" in row.get("test_group", "") else "100%"
    orientation = row.get("optimization", "")
    return {
        "id": row["record_id"], "machine": row["machine"], "speed": speed,
        "orientation": orientation, "length": length, "width": width,
        "area": a * b, "time": time, "seconds_per_m": time / length,
        "seconds_per_area": time / (a * b),
    }


def mean(values):
    return sum(values) / len(values) if values else None


def fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def mixed_analysis(rows):
    parsed = [p for row in rows if row.get("measurement_type", "").lower().startswith("mixed") and (p := parse_mixed(row))]
    print("\n=== LINE/SPLINE CUT TESTS ===")
    if not parsed:
        print("No parsable mixed line/spline observations.")
        return
    groups = defaultdict(list)
    for p in parsed:
        groups[(p["group"], p["machine"], p["optimization"])].append(p)
    for key, group in sorted(groups.items()):
        print(f"\n{key[0]} | {key[1]} | JcT={key[2]} | n={len(group)}")
        print("  ID       distance(mm) line% spline%   time(s)   sec/m")
        for p in sorted(group, key=lambda x: x["distance"]):
            print(f"  {p['id']:<8} {p['distance']:>9.0f} {p['line_fraction']*100:>5.0f} {p['spline_fraction']*100:>6.0f} {p['time']:>9.0f} {p['seconds_per_m']:>8.2f}")
        # A descriptive least-squares slope of time against distance within this
        # group; no extrapolation or estimator claim is made.
        xs = [p["distance"] / 1000 for p in group]
        ys = [p["time"] for p in group]
        xbar, ybar = mean(xs), mean(ys)
        denom = sum((x-xbar)**2 for x in xs)
        slope = sum((x-xbar)*(y-ybar) for x,y in zip(xs,ys))/denom if denom else None
        intercept = ybar - slope*xbar if slope is not None else None
        print(f"  Descriptive time-vs-distance slope: {fmt(slope)} s/m; intercept {fmt(intercept)} s")
        print("  NOTE: this slope is not a generalized cut-rate coefficient.")

    # Composition comparison at fixed distances within groups.
    print("\nComposition comparisons (same distance within a group):")
    for key, group in sorted(groups.items()):
        by_distance = defaultdict(list)
        for p in group:
            by_distance[p["distance"]].append(p)
        for distance, entries in sorted(by_distance.items()):
            if len(entries) > 1:
                entries.sort(key=lambda p: p["spline_fraction"])
                print(f"  {key} | {distance:.0f} mm | " + " vs ".join(
                    f"{p['spline_fraction']:.0%} spline: {p['time']:.0f}s" for p in entries
                ))


def fill_analysis(rows):
    parsed = [p for row in rows if row.get("measurement_type", "").lower().startswith("filled") and (p := parse_fill(row))]
    print("\n=== FILLED ENGRAVING TESTS ===")
    if not parsed:
        print("No parsable filled-engraving observations.")
        return
    groups = defaultdict(list)
    for p in parsed:
        groups[(p["machine"], p["speed"], p["orientation"])].append(p)
    for key, group in sorted(groups.items()):
        print(f"\n{key[0]} | speed={key[1]} | orientation={key[2]} | n={len(group)}")
        print("  ID       dimensions    area(mm²)   time(s)   sec/m    sec/mm²")
        for p in sorted(group, key=lambda x: x["length"]):
            print(f"  {p['id']:<8} {p['width']:g}x{p['length']:g}       {p['area']:>8.0f} {p['time']:>9.0f} {p['seconds_per_m']:>8.2f} {p['seconds_per_area']:>10.4f}")
        # Descriptive fit of runtime to rectangle length for this fixed-width
        # series; only three observations are present in each such subgroup.
        xs = [p["length"] for p in group]
        ys = [p["time"] for p in group]
        xbar, ybar = mean(xs), mean(ys)
        denom = sum((x-xbar)**2 for x in xs)
        slope = sum((x-xbar)*(y-ybar) for x,y in zip(xs,ys))/denom if denom else None
        intercept = ybar - slope*xbar if slope is not None else None
        print(f"  Descriptive time-vs-length slope: {fmt(slope)} s/mm; intercept {fmt(intercept)} s")

    print("\nOrientation comparison (matched machine/speed/rectangle):")
    paired = defaultdict(dict)
    for p in parsed:
        paired[(p["machine"], p["speed"], p["length"], p["width"])][p["orientation"].lower()] = p["time"]
    for key, vals in sorted(paired.items()):
        if len(vals) >= 2:
            labels = list(vals)
            print(f"  {key[0]} {key[1]} {key[3]:g}x{key[2]:g}: " +
                  " | ".join(f"{label}={time:.0f}s" for label,time in vals.items()))

    print("\nSpeed comparison (matched machine/orientation/rectangle):")
    paired = defaultdict(dict)
    for p in parsed:
        paired[(p["machine"], p["orientation"], p["length"], p["width"])][p["speed"]] = p["time"]
    for key, vals in sorted(paired.items()):
        if "50%" in vals and "100%" in vals:
            ratio = vals["50%"] / vals["100%"] if vals["100%"] else None
            print(f"  {key[0]} {key[1]} {key[3]:g}x{key[2]:g}: 50%={vals['50%']:.0f}s / 100%={vals['100%']:.0f}s; ratio={fmt(ratio)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    rows = load_rows(args.data)
    print(f"Controlled calibration analysis: {len(rows)} records ({args.data})")
    print("DESCRIPTIVE / EXPERIMENTAL ONLY — no deployable coefficients are generated.")
    mixed_analysis(rows)
    fill_analysis(rows)
    print("\n=== LIMITATIONS ===")
    print("* These are descriptive analyses of reported controlled tests, not validated predictions.")
    print("* Source notes identify possible measurement and geometry ambiguities.")
    print("* No production observations are included in this analysis.")
    print("* Do not extrapolate outside tested machines, speeds, settings or geometries.")


if __name__ == "__main__":
    main()
