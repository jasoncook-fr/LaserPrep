#!/usr/bin/env python3
"""Create separately adjusted copies of laser LCF profiles.

Original profiles are never modified. Speed values are scaled by a configurable
factor (default 0.90); power and all other parameters are preserved.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

DEFAULT_SPEED_FACTOR = 0.90
HEADER_RE = re.compile(r"^\s*\[([^]]+)\]\s*$")
KEY_RE = re.compile(r"^(\s*Speed\s*=\s*)(.*?)(\s*)$", re.IGNORECASE)


def parse_speed_values(value: str) -> list[int]:
    tokens = value.split()
    if not tokens:
        raise ValueError("Speed entry contains no values")
    values = []
    for token in tokens:
        if not re.fullmatch(r"[+-]?\d+", token):
            raise ValueError(f"Non-integer speed value: {token!r}")
        values.append(int(token))
    return values


def adjust_lcf_text(text: str, speed_factor: float, source_name: str = "") -> tuple[str, list[dict]]:
    if not (0 < speed_factor <= 1.5):
        raise ValueError("speed_factor must be greater than 0 and at most 1.5")
    out_lines = []
    audits = []
    section = ""
    for line_number, line in enumerate(text.splitlines(keepends=True), 1):
        match_header = HEADER_RE.match(line.rstrip("\r\n"))
        if match_header:
            section = match_header.group(1).strip()
        match = KEY_RE.match(line.rstrip("\r\n"))
        if not match:
            out_lines.append(line)
            continue
        prefix, value, whitespace = match.groups()
        original = parse_speed_values(value)
        if len(original) != 8:
            raise ValueError(
                f"{source_name or '<input>'}:{line_number}: expected 8 speed slots, found {len(original)}"
            )
        adjusted = [int(round(v * speed_factor)) for v in original]
        for slot, (old, new) in enumerate(zip(original, adjusted), 1):
            audits.append({
                "source_file": source_name,
                "section": section,
                "line_number": line_number,
                "slot": slot,
                "original_speed_raw": old,
                "adjusted_speed_raw": new,
                "speed_factor": speed_factor,
            })
        newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        out_lines.append(prefix + " ".join(map(str, adjusted)) + whitespace + newline)
    if not audits:
        raise ValueError(f"No Speed entry found in {source_name or '<input>'}")
    return "".join(out_lines), audits


def process_directory(input_dir: Path, output_dir: Path, speed_factor: float = DEFAULT_SPEED_FACTOR) -> list[dict]:
    input_dir, output_dir = input_dir.resolve(), output_dir.resolve()
    if input_dir == output_dir or input_dir in output_dir.parents or output_dir in input_dir.parents:
        raise ValueError("Input and output directories must not overlap")
    files = sorted(input_dir.rglob("*.lcf"))
    if not files:
        raise ValueError(f"No .lcf files found in {input_dir}")
    audits = []
    for source in files:
        relative = source.relative_to(input_dir)
        destination = output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        original_text = source.read_text(encoding="utf-8", errors="strict")
        adjusted_text, file_audit = adjust_lcf_text(original_text, speed_factor, str(relative))
        destination.write_text(adjusted_text, encoding="utf-8")
        audits.extend(file_audit)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / "speed_adjustment_audit.csv"
    with audit_path.open("w", newline="", encoding="utf-8") as handle:
        fields = list(audits[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audits)
    summary = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "speed_factor": speed_factor,
        "profile_files": len(files),
        "speed_slots_adjusted": len(audits),
        "power_adjustments": "none; original values preserved",
        "audit_file": audit_path.name,
    }
    (output_dir / "adjustment_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return audits


def main() -> None:
    parser = argparse.ArgumentParser(description="Create adjusted copies of LCF profiles.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--speed-factor", type=float, default=DEFAULT_SPEED_FACTOR,
                        help="Multiplier for speed values (default: 0.90)")
    args = parser.parse_args()
    audits = process_directory(args.input_dir, args.output_dir, args.speed_factor)
    print(f"Adjusted {len(audits)} speed slots.")
    print(f"Output: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
