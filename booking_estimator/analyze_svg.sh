#!/usr/bin/env bash
# Analyze a single SVG using LaserPrep's experimental booking-estimator modules.
# Run from the LaserPrep repository root: bash booking_estimator/analyze_svg.sh FILE.svg
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash booking_estimator/analyze_svg.sh FILE.svg [--json OUTPUT.json]

Analyze a single SVG and print geometry/workload features.
This does not predict laser runtime.
EOF
}

if [[ $# -lt 1 ]]; then usage; exit 2; fi
SVG_FILE="$1"; shift
JSON_OUT=""
if [[ $# -gt 0 ]]; then
  if [[ "$1" == "--json" && $# -ge 2 ]]; then JSON_OUT="$2"; shift 2
  else usage; exit 2
  fi
fi
if [[ $# -gt 0 ]]; then usage; exit 2; fi
if [[ ! -f "$SVG_FILE" ]]; then echo "Error: SVG file not found: $SVG_FILE" >&2; exit 2; fi

# Locate repository root from script location and ensure imports work.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

SVG_FILE="$(realpath "$SVG_FILE")"
if [[ -n "$JSON_OUT" ]]; then JSON_OUT="$(realpath -m "$JSON_OUT")"; fi

python - "$SVG_FILE" "$JSON_OUT" <<'PY'
import json, sys
from pathlib import Path
from booking_estimator.geometry_measurement import analyze_svg_geometry
from booking_estimator.workload_features import build_workload_features

svg_path = Path(sys.argv[1])
json_path = sys.argv[2]
try:
    measurement = analyze_svg_geometry(svg_path.read_text(encoding="utf-8"))
    features = build_workload_features(measurement)
except Exception as exc:
    print(f"Analysis failed: {exc}", file=sys.stderr)
    raise SystemExit(1)

p, c, s, o = (features["profile"], features["complexity"],
               features["spatial"], features["operations"])
warnings = features.get("warnings", [])

print(f"SVG: {svg_path}")
print("=" * 60)
print(f"Coverage status: {features.get('coverage_status', 'unknown')}")
print(f"Coverage warnings: {len(warnings)}")
print(f"Elements: {p['element_count']}")
print(f"Segments: {p['segment_count']}")
print(f"Total geometry length: {p['total_length_mm']:.2f} mm")
print(f"  Lines: {p['line_length_mm']:.2f} mm")
print(f"  Curves: {p['curve_length_mm']:.2f} mm")
print(f"Short segments (< {p['short_segment_threshold_mm']:g} mm): "
      f"{p['short_segment_count']} ({p['short_segment_fraction']:.1%})")
print(f"Mean segment length: {p['mean_segment_length_mm']:.3f} mm")
print(f"Open / closed elements: {p['open_element_count']} / {p['closed_element_count']}")
print()
print("Turning / complexity:")
print(f"  Connected transitions: {c['transition_count']}")
print(f"  Mean turn: {c['mean_turn_angle_deg']:.2f} degrees")
print(f"  Maximum turn: {c['maximum_turn_angle_deg']:.2f} degrees")
print(f"  Total turn: {c['total_turn_angle_deg']:.2f} degrees")
print(f"  Turn density: {c['turn_density_per_m']:.2f} degrees/m")
print()
print("Spatial distribution (coarse bounding-box-centroid proxy):")
print(f"  Document bounds: {p['document_bbox_width_mm']:.2f} x "
      f"{p['document_bbox_height_mm']:.2f} mm")
print(f"  Occupied cells: {s['occupied_cells']}/{s['grid_size']**2}")
print(f"  Largest cell fraction of length: {s['max_cell_fraction_of_total']:.1%}")
print(f"  Normalized entropy: {s['spatial_entropy_normalized']:.3f}")
print()
print("Operation classification:")
print(f"  Unclassified elements: {o['unclassified_element_count']}")
print("  (Automatic color/style-to-operation mapping is not implemented.)")

if warnings:
    print()
    print("Warnings:")
    for w in warnings:
        if isinstance(w, dict):
            print(f"  - {w.get('source_id') or w.get('element_type') or 'item'}: "
                  f"{w.get('message', w)}")
        else:
            print(f"  - {w}")

if json_path:
    report = {"input_file": str(svg_path), "measurement": measurement,
              "workload_features": features}
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(report, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    print(f"\nFull JSON report saved: {json_path}")

print()
print("NOTE: Descriptive analysis only — not a calibrated runtime estimate.")
PY
