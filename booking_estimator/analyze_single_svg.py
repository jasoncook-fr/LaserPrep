#!/usr/bin/env python3
"""Analyze one SVG with the experimental LaserPrep booking estimator.

This reports descriptive geometry/workload features only. It does not predict
laser runtime or classify operations automatically.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from booking_estimator.geometry_measurement import analyze_svg_geometry
from booking_estimator.workload_features import build_workload_features


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a single SVG with the experimental booking estimator.")
    parser.add_argument("svg", type=Path, help="SVG file to analyze")
    parser.add_argument("--json", dest="json_path", type=Path, help="Optional path to save the complete feature report as JSON")
    parser.add_argument("--grid", type=int, default=4, help="Spatial-analysis grid size (default: 4)")
    parser.add_argument("--short-segment", type=float, default=1.0, help="Short-segment threshold in mm (default: 1.0)")
    args = parser.parse_args()

    if not args.svg.is_file():
        parser.error(f"SVG file not found: {args.svg}")

    try:
        measurement = analyze_svg_geometry(args.svg.read_text(encoding="utf-8"))
        features = build_workload_features(
            measurement, grid_size=args.grid,
            short_segment_threshold_mm=args.short_segment,
        )
    except Exception as exc:
        parser.exit(2, f"Analysis failed: {exc}\n")

    p = features["profile"]
    c = features["complexity"]
    s = features["spatial"]
    o = features["operations"]

    print(f"SVG: {args.svg}")
    print("=" * 60)
    print(f"Coverage: {features['coverage_status']} ({len(features['warnings'])} warning(s))")
    print(f"Measured elements: {p['element_count']}")
    print(f"Segments: {p['segment_count']}")
    print(f"Total length: {p['total_length_mm']:.2f} mm")
    print(f"  Straight-line length: {p['line_length_mm']:.2f} mm")
    print(f"  Curve length: {p['curve_length_mm']:.2f} mm")
    print(f"Short segments (< {args.short_segment:g} mm): {p['short_segment_count']} ({p['short_segment_fraction']:.1%})")
    print(f"Mean segment length: {p['mean_segment_length_mm']:.3f} mm")
    print(f"Open / closed elements: {p['open_element_count']} / {p['closed_element_count']}")
    print()
    print("Turning / complexity")
    print(f"  Connected transitions: {c['transition_count']}")
    print(f"  Mean turn angle: {c['mean_turn_angle_deg']:.2f} deg")
    print(f"  Maximum turn angle: {c['maximum_turn_angle_deg']:.2f} deg")
    print(f"  Total turn angle: {c['total_turn_angle_deg']:.2f} deg")
    print(f"  Turn density: {c['turn_density_per_m']:.2f} deg/m")
    print()
    print("Spatial proxy")
    print(f"  Document bounds: {p['document_bbox_width_mm']:.2f} x {p['document_bbox_height_mm']:.2f} mm")
    print(f"  Occupied grid cells: {s['occupied_cells']}/{args.grid * args.grid}")
    print(f"  Largest cell share of length: {s['max_cell_fraction_of_total']:.1%}")
    print(f"  Normalized spatial entropy: {s['spatial_entropy_normalized']:.3f}")
    print()
    print("Operation classification")
    print(f"  Unclassified elements: {o['unclassified_element_count']}")
    print("  (No automatic color/style-to-operation mapping is applied.)")

    if features["warnings"]:
        print()
        print("Coverage warnings")
        for warning in features["warnings"]:
            print(f"  - {warning.get('source_id') or warning.get('element_type')}: {warning.get('message')}")
    print()
    print("NOTE: This is a geometry/workload analysis, not a runtime prediction.")

    report = {"input_file": str(args.svg), "measurement": measurement, "workload_features": features}
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Full report written: {args.json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
