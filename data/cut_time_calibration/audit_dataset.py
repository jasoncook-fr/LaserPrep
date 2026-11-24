#!/usr/bin/env python3
"""Audit the cut-time calibration dataset before fitting experimental models.

This intentionally does not fit or alter a production estimator. It reports data
coverage, flags incomplete records, and identifies identical-geometry paired
production observations that may be useful for controlled comparisons.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRODUCTION = ROOT / "production_jobs_master.csv"
CONTROLLED = ROOT / "controlled_tests_master.csv"

PRODUCTION_FEATURES = (
    "machine", "actual_time_seconds", "path_count", "blue_cut_paths",
    "green_engrave_paths", "red_engrave_paths", "black_fill_paths",
    "optimisation", "profile_filename", "material", "blue_cut_straight_mm",
    "blue_cut_curves_mm", "green_vector_mm", "red_vector_mm",
    "black_fill_area_mm2",
)
CONTROLLED_FEATURES = (
    "machine", "optimization", "measurement_type", "geometry",
    "actual_time_seconds",
)


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def populated(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def report_stream(label: str, rows: list[dict[str, str]], features: tuple[str, ...]) -> None:
    print(f"\n{label}: {len(rows)} records")
    if not rows:
        print("  Dataset missing or empty.")
        return
    for feature in features:
        count = sum(populated(row.get(feature)) for row in rows)
        print(f"  {feature:28} {count:>4}/{len(rows)} ({count/len(rows):.0%})")
    machines = Counter(row.get("machine", "") or "unknown" for row in rows)
    print("  machine distribution:", dict(machines))


def production_pair_candidates(rows: list[dict[str, str]]) -> None:
    # Only compare records where geometry values are all present. The geometry
    # signature is deliberately independent of runtime and machine/settings.
    geometry_fields = (
        "path_count", "blue_cut_paths", "green_engrave_paths",
        "red_engrave_paths", "black_fill_paths", "blue_cut_straight_mm",
        "blue_cut_curves_mm", "green_vector_mm", "red_vector_mm",
        "black_fill_area_mm2",
    )
    buckets: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if all(populated(row.get(field)) for field in geometry_fields):
            signature = tuple(row[field].strip() for field in geometry_fields)
            buckets[signature].append(row)
    candidates = [bucket for bucket in buckets.values() if len(bucket) > 1]
    print(f"\nComplete geometry signatures shared by multiple production records: {len(candidates)}")
    for bucket in candidates:
        print("  " + " | ".join(
            f"{row.get('job_id','?')} {row.get('machine','?')} "
            f"{row.get('actual_time_seconds','?')}s [{row.get('optimisation','?')}]"
            for row in bucket
        ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", type=Path, default=PRODUCTION)
    parser.add_argument("--controlled", type=Path, default=CONTROLLED)
    args = parser.parse_args()

    production = load_csv(args.production)
    controlled = load_csv(args.controlled)
    report_stream("Production jobs", production, PRODUCTION_FEATURES)
    report_stream("Controlled tests", controlled, CONTROLLED_FEATURES)
    production_pair_candidates(production)

    print("\nInterpretation:")
    print("  * Blank fields are unknown, not zero.")
    print("  * Controlled tests and production jobs remain separate streams.")
    print("  * Shared geometry is a candidate for paired comparison, not proof of a controlled run.")
    print("  * No coefficients or estimates are calculated by this audit.")


if __name__ == "__main__":
    main()
