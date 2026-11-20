#!/usr/bin/env python3
"""Isolated experimental effective-rate estimate from historical geometry CSV.

Prototype only. Benchmark geometry is currently hard-coded and this is not
integrated into LaserPrep production processing or rejection decisions.
"""
import csv
import re
from pathlib import Path

DATA = Path("data/cut_time_calibration/analysis_output/geometry_extraction/geometry_summary.csv")
BENCHMARK = {
    "machine": "60W",
    "optimization": "ON",
    "cut_mm": 18787.697,
    "vector_mm": 38511.993,
    "black_mm": 13920.172,
    "paths": 3491,
}

def parse_filename(filename):
    match = re.match(r"^(\d+)m(\d+)s_", filename)
    if not match:
        return None
    seconds = int(match.group(1))*60 + int(match.group(2))
    machine = re.search(r"_(60W|100W)_", filename)
    opt = re.search(r"OPT[_-](ON|OFF)", filename, re.IGNORECASE)
    if not machine:
        return None
    return seconds, machine.group(1), opt.group(1).upper() if opt else "UNKNOWN"

def main():
    samples = {}
    with DATA.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            parsed = parse_filename(row["filename"])
            if parsed is None:
                continue
            seconds, machine, optimization = parsed
            length = sum(float(row.get(k) or 0) for k in
                ("blue_cut_mm", "red_green_vector_mm", "black_stroke_mm"))
            if length <= 0:
                continue
            samples.setdefault((machine, optimization), []).append(
                {"filename": row["filename"], "seconds": seconds, "length": length})

    for key, records in sorted(samples.items()):
        rate = sum(r["length"] for r in records)/sum(r["seconds"] for r in records)
        print(f"\n{key[0]} / OPT_{key[1]} ({len(records)} samples): pooled {rate:.2f} mm/s")
        for r in records:
            print(f"  {r['filename']}: {r['length']:.0f} mm / {r['seconds']} s = {r['length']/r['seconds']:.2f} mm/s")

    key = (BENCHMARK["machine"], BENCHMARK["optimization"])
    records = samples.get(key, [])
    if not records:
        print("\nNo matching samples for benchmark.")
        return
    rate = sum(r["length"] for r in records)/sum(r["seconds"] for r in records)
    total = BENCHMARK["cut_mm"]+BENCHMARK["vector_mm"]+BENCHMARK["black_mm"]
    seconds = total/rate
    print("\nBENCHMARK #001")
    print(f"Machine: {key[0]} | Optimization: {key[1]}")
    print(f"Total geometry: {total:,.0f} mm | Effective rate: {rate:.2f} mm/s")
    print(f"Estimated time: {seconds/60:.2f} minutes ({seconds:.0f} seconds)")

if __name__ == "__main__":
    main()
