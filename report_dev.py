"""
report_dev.py

Developer report for LaserPrep.
Produces the detailed diagnostics that were removed from the
operator report.
"""

from pathlib import Path
from datetime import datetime


class DeveloperReport:

    def __init__(self):
        self.lines = []

    def section(self, name):
        self.lines.extend(["", name, "-" * 60])

    def line(self, label, value):
        self.lines.append(f"{label:<22} : {value}")

    def begin_file(self, filename):
        self.lines.extend([
            "",
            "=" * 60,
            filename,
            "=" * 60,
        ])

    def validation(self, drawing, rotated, overflow, large_ok, small_ok):
        self.section("Validation")
        self.line("Drawing Size", f"{drawing.drawing_width:.2f} × {drawing.drawing_height:.2f} mm")
        self.line("Orientation", "Rotated" if rotated else "Original")
        self.line("Overflow", f"{overflow:.2f} mm")
        self.line("Large Laser", "YES" if large_ok else "NO")
        self.line("Small Laser", "YES" if small_ok else "NO")

    def complexity(self, complexity):
        self.section("Complexity")
        self.line("Vector objects", complexity.object_count)
        self.line("Rating", complexity.rating)
        self.line("Abort", complexity.should_abort)

    def geometry(self, geometry):
        self.section("Geometry")
        self.line("Zero-length lines", geometry.zero_length_lines)
        self.line("Tiny segments", geometry.tiny_lines)
        self.line("Duplicate lines", geometry.duplicate_lines)
        if geometry.shortest_line_mm is not None:
            self.line("Shortest segment", f"{geometry.shortest_line_mm:.6f} mm")

    def colours(self, colours):
        self.section("Colours")

        self.lines.append("")
        self.lines.append("Official colours")
        for name, count in colours.official.items():
            self.line(name, count)

        if colours.near:
            self.lines.append("")
            self.lines.append("Near official")
            for rgb, info in sorted(colours.near.items()):
                self.lines.append(
                    f"{rgb} -> {info['target']} ({info['count']})"
                )

        if colours.unsupported:
            self.lines.append("")
            self.lines.append("Unsupported")
            for rgb, count in sorted(colours.unsupported.items()):
                self.lines.append(f"{rgb} : {count}")

    def cleanup(self, removed_zero, removed_duplicates, corrected):
        self.section("Cleanup")
        self.line("Zero-length removed", removed_zero)
        self.line("Duplicates removed", removed_duplicates)
        self.line("Colours corrected", corrected)

    def statistics(self, stats):
        self.section("Geometry Statistics")
        self.line("Total lines", stats.total_lines)
        self.line("< 0.01 mm", stats.lt_001)
        self.line("0.01-0.05 mm", stats.lt_005)
        self.line("0.05-0.10 mm", stats.lt_010)
        self.line("0.10-0.50 mm", stats.lt_050)
        self.line("0.50-1.00 mm", stats.lt_100)
        self.line("> 1.00 mm", stats.gt_100)

    def chains(self, chains):
        self.section("Geometry Chains")
        self.line("Total chains", chains.total_chains)
        self.line("Longest chain", chains.longest_chain)

        avg = (
            chains.total_segments / chains.total_chains
            if chains.total_chains else 0
        )
        self.line("Average chain", f"{avg:.1f}")

        self.lines.append("")
        self.lines.append("Distribution")
        self.line("1 segment", chains.one)
        self.line("2-5 segments", chains.two_to_five)
        self.line("6-20 segments", chains.six_to_twenty)
        self.line("21-100 segments", chains.twentyone_to_hundred)
        self.line(">100 segments", chains.over_hundred)

    def save(self, filename, project):
        header = [
            "=" * 60,
            "LASERPREP DEVELOPER REPORT",
            "=" * 60,
            f"Project   : {project}",
            f"Generated : {datetime.now():%Y-%m-%d %H:%M:%S}",
            "",
        ]
        Path(filename).write_text(
            "\n".join(header + self.lines),
            encoding="utf-8",
        )


