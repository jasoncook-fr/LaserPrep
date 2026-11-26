#!/usr/bin/env bash
# Batch analyze SVG files in a directory using the experimental estimator.
# Usage: bash booking_estimator/batch_analyze.sh INPUT_DIR [OUTPUT_DIR]
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash booking_estimator/batch_analyze.sh INPUT_DIR [OUTPUT_DIR]" >&2
  exit 2
fi
INPUT_DIR="$1"
OUTPUT_DIR="${2:-${INPUT_DIR%/}/booking_estimator_results}"
if [[ ! -d "$INPUT_DIR" ]]; then echo "Error: input directory not found: $INPUT_DIR" >&2; exit 2; fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
INPUT_DIR="$(realpath "$INPUT_DIR")"
OUTPUT_DIR="$(realpath -m "$OUTPUT_DIR")"
mkdir -p "$OUTPUT_DIR"
python - "$INPUT_DIR" "$OUTPUT_DIR" <<'PY'
import csv, json, sys, traceback
from pathlib import Path
from booking_estimator.geometry_measurement import analyze_svg_geometry
from booking_estimator.workload_features import build_workload_features

input_dir, output_dir = map(Path, sys.argv[1:])
files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower()==".svg")
if not files:
    print(f"No SVG files found in {input_dir}")
    raise SystemExit(0)

rows=[]
failures=[]
for path in files:
    rel=path.relative_to(input_dir)
    safe_name=rel.with_suffix("")
    json_path=output_dir/(str(safe_name)+".json")
    json_path.parent.mkdir(parents=True,exist_ok=True)
    print(f"[{len(rows)+len(failures)+1}/{len(files)}] {rel}",flush=True)
    try:
        measurement=analyze_svg_geometry(path.read_text(encoding="utf-8"))
        features=build_workload_features(measurement)
        p,c,s,o=(features["profile"],features["complexity"],features["spatial"],features["operations"])
        report={"input_file":str(path),"relative_path":str(rel),"measurement":measurement,"workload_features":features}
        json_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        rows.append({
          "file":str(rel),"analysis_status":"ok","coverage_status":features.get("coverage_status"),
          "coverage_complete":features.get("coverage_complete"),"warning_count":len(features.get("warnings",[])),
          "element_count":p["element_count"],"segment_count":p["segment_count"],
          "total_length_mm":round(p["total_length_mm"],4),"line_length_mm":round(p["line_length_mm"],4),
          "curve_length_mm":round(p["curve_length_mm"],4),"short_segment_count":p["short_segment_count"],
          "short_segment_fraction":round(p["short_segment_fraction"],6),
          "mean_segment_length_mm":round(p["mean_segment_length_mm"],4),
          "open_element_count":p["open_element_count"],"closed_element_count":p["closed_element_count"],
          "transition_count":c["transition_count"],"mean_turn_angle_deg":round(c["mean_turn_angle_deg"],4),
          "maximum_turn_angle_deg":round(c["maximum_turn_angle_deg"],4),
          "total_turn_angle_deg":round(c["total_turn_angle_deg"],4),"turn_density_per_m":round(c["turn_density_per_m"],4),
          "document_width_mm":round(p["document_bbox_width_mm"],4),"document_height_mm":round(p["document_bbox_height_mm"],4),
          "occupied_cells":s["occupied_cells"],"spatial_entropy_normalized":round(s["spatial_entropy_normalized"],6),
          "unclassified_element_count":o["unclassified_element_count"],"json_report":str(json_path.relative_to(output_dir)),
          "error":""})
    except Exception as exc:
        failures.append({"file":str(rel),"error":str(exc)})
        rows.append({"file":str(rel),"analysis_status":"error","error":str(exc)})
        print(f"  ERROR: {exc}",file=sys.stderr)

csv_path=output_dir/"summary.csv"
columns=list(rows[0].keys())
with csv_path.open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
    writer.writeheader();writer.writerows(rows)
summary={"input_directory":str(input_dir),"output_directory":str(output_dir),
         "total_svg_files":len(files),"successful":len(rows)-len(failures),
         "failed":len(failures),"failed_files":failures,"summary_csv":str(csv_path)}
(output_dir/"batch_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
print("\nBatch complete.")
print(f"  SVG files: {len(files)} | Successful: {len(rows)-len(failures)} | Failed: {len(failures)}")
print(f"  CSV: {csv_path}")
print(f"  JSON reports: {output_dir}")
PY
