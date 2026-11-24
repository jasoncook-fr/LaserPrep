#!/usr/bin/env python3
"""Standalone, read-only, section-aware analyzer for LaserPrep LCF profiles."""
from __future__ import annotations
import argparse, csv, hashlib, json
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "data" / "cut_time_calibration" / "lcf_files"
OUTPUT_DIR = BASE_DIR / "data" / "cut_time_calibration" / "analysis_output"
MACHINES = ("60W", "100W")


def parse_lcf(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current = "(no section)"
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith((";", "#")):
            continue
        if s.startswith("[") and s.endswith("]"):
            current = s[1:-1].strip()
            sections.setdefault(current, {})
        elif "=" in s:
            key, value = s.split("=", 1)
            sections.setdefault(current, {})[key.strip()] = value.strip()
    return sections


def tokens(value: str) -> list[str]:
    return value.split()


def digest(section: dict[str, str]) -> str:
    payload = json.dumps(section, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-dir", type=Path, default=PROFILE_DIR)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = ap.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for folder_machine in MACHINES:
        folder = args.profile_dir / folder_machine
        if not folder.is_dir():
            raise SystemExit(f"Missing expected directory: {folder}")
        for path in sorted(folder.glob("*.lcf"), key=lambda p: p.name.casefold()):
            sections = parse_lcf(path)
            for section_name, values in sections.items():
                records.append({
                    "folder_machine": folder_machine,
                    "filename": path.name,
                    "relative_path": str(path.relative_to(args.profile_dir)),
                    "section": section_name,
                    "values": values,
                    "hash": digest(values),
                })
    if not records:
        raise SystemExit("No profiles found.")

    keys = sorted({k for r in records for k in r["values"]})
    csv_path = out / "lcf_profiles.csv"
    fields = ["folder_machine", "filename", "relative_path", "section", "key_count", "section_hash"] + keys
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            row = {"folder_machine": r["folder_machine"], "filename": r["filename"],
                   "relative_path": r["relative_path"], "section": r["section"],
                   "key_count": len(r["values"]), "section_hash": r["hash"]}
            row.update(r["values"])
            w.writerow(row)

    json_path = out / "lcf_profiles.json"
    json_path.write_text(json.dumps([{
        "folder_machine": r["folder_machine"], "filename": r["filename"],
        "relative_path": r["relative_path"], "section": r["section"],
        "hash": r["hash"], "values": r["values"]
    } for r in records], indent=2, ensure_ascii=False), encoding="utf-8")

    report = ["# LCF Profile Inventory and Structural Analysis", "",
              "> Read-only analysis of profiles in the configured 60W and 100W folders. Each LCF section is analyzed as a separate record. No parameter semantics or array positions are inferred.", "",
              "## Dataset", "", f"- Source files: **{sum(1 for m in MACHINES for _ in (args.profile_dir / m).glob('*.lcf'))}**",
              f"- Section records: **{len(records)}**"]
    for m in MACHINES:
        fs = list((args.profile_dir / m).glob("*.lcf"))
        rs = [r for r in records if r["folder_machine"] == m]
        report.append(f"- {m} folder: **{len(fs)} files**, **{len(rs)} sections/records**")
    report += ["", "## Sections encountered", "", "| Section | Records | Folder origin |", "|---|---:|---|"]
    for sec in sorted({r["section"] for r in records}):
        origins = Counter(r["folder_machine"] for r in records if r["section"] == sec)
        report.append(f"| `{sec}` | {sum(origins.values())} | " + ", ".join(f"{m}: {n}" for m,n in origins.items()) + " |")

    report += ["", "## Key coverage across section records", "", "| Key | Present | Missing | Unique raw values | Multi-token records | Token lengths |", "|---|---:|---:|---:|---:|---|"]
    for k in keys:
        vals = [r["values"][k] for r in records if k in r["values"]]
        lens = [len(tokens(v)) for v in vals]
        multi = [n for n in lens if n > 1]
        report.append(f"| `{k}` | {len(vals)} | {len(records)-len(vals)} | {len(set(vals))} | {len(multi)} | {', '.join(map(str,sorted(set(multi)))) or '—'} |")

    report += ["", "## Raw-value variation by folder origin", ""]
    for m in MACHINES:
        subset = [r for r in records if r["folder_machine"] == m]
        report += [f"### {m}", "", "| Key | Records containing key | Unique values |", "|---|---:|---:|"]
        for k in keys:
            vals = [r["values"][k] for r in subset if k in r["values"]]
            if len(set(vals)) > 1:
                report.append(f"| `{k}` | {len(vals)} | {len(set(vals))} |")
        report.append("")

    report += ["## Exact section-content duplicates", "", "Identical section dictionaries are grouped regardless of filename or folder origin.", ""]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records: groups[r["hash"]].append(r)
    dup = [g for g in groups.values() if len(g) > 1]
    if not dup:
        report.append("No identical section-content groups detected.")
    else:
        for g in dup:
            report.append("- " + "; ".join(f"{r['folder_machine']}/{r['filename']} [{r['section']}]" for r in g))

    report += ["", "## Array/token-length observations", "", "Lengths are descriptive only; token positions are not interpreted.", ""]
    for k in keys:
        rows = [(r, len(tokens(r["values"][k]))) for r in records if k in r["values"] and len(tokens(r["values"][k])) > 1]
        if rows:
            dist = Counter(n for _,n in rows)
            report += [f"### `{k}`", "", f"- Multi-token records: **{len(rows)}**", "- Length distribution: " + ", ".join(f"{n}: {dist[n]}" for n in sorted(dist)), ""]

    report += ["## Data preservation", "", "- JSON retains the complete parsed key/value dictionary for each section record.", "- CSV contains one row per section record, with raw values.", "- Folder origin and actual section name are retained separately.", "- No array channel mapping or parameter semantics are inferred.", ""]
    report_path = out / "lcf_analysis_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Analyzed {len(records)} section records from {sum(1 for m in MACHINES for _ in (args.profile_dir/m).glob('*.lcf'))} files.")
    print(f"CSV: {csv_path}\nJSON: {json_path}\nReport: {report_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
