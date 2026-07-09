"""
============================================================
LaserPrep Diagnostics
Version : 2.2B
Milestone : 1.1
============================================================

Central diagnostics system.

Responsibilities
----------------
* Debug enable/disable
* Debug folder management
* Report generation
* Logging
* Statistics

Future milestones
-----------------
* SVG export
* Colour-coded debug exports
* Timing
* Cleanup statistics
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

from config import DEBUG_MODE


# ============================================================
# DIAGNOSTICS
# ============================================================

class Diagnostics:

    def __init__(self):

        self.enabled = DEBUG_MODE

        self.project = ""
        self.project_folder = None
        self.debug_folder = None

        self.report_lines = []

    # --------------------------------------------------------
    # INITIALIZATION
    # --------------------------------------------------------

    def begin(self, project: str, project_folder):

        if not self.enabled:
            return

        self.project = project
        self.project_folder = Path(project_folder)

        self.debug_folder = self.project_folder / "debug"
        self.debug_folder.mkdir(parents=True, exist_ok=True)

        self.report_lines = []

        self._write_header()

    # --------------------------------------------------------

    def end(self):

        if not self.enabled:
            return

        report_file = self.debug_folder / "report.txt"

        report_file.write_text(
            "\n".join(self.report_lines),
            encoding="utf-8",
        )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    def _write_header(self):

        self.report_lines.append(
            "=" * 60
        )

        self.report_lines.append(
            "LASERPREP DIAGNOSTICS"
        )

        self.report_lines.append(
            "=" * 60
        )

        self.report_lines.append(
            f"Project : {self.project}"
        )

        self.report_lines.append(
            f"Started : {datetime.now()}"
        )

        self.report_lines.append("")

    # --------------------------------------------------------

    def section(self, title: str):

        if not self.enabled:
            return

        self.report_lines.append("")
        self.report_lines.append(title)
        self.report_lines.append("-" * len(title))

    # --------------------------------------------------------

    def info(self, message: str):

        if not self.enabled:
            return

        self.report_lines.append(
            f"[INFO] {message}"
        )

    # --------------------------------------------------------

    def warning(self, message: str):

        if not self.enabled:
            return

        self.report_lines.append(
            f"[WARNING] {message}"
        )

    # --------------------------------------------------------

    def error(self, message: str):

        if not self.enabled:
            return

        self.report_lines.append(
            f"[ERROR] {message}"
        )

    # --------------------------------------------------------

    def stat(self, label: str, value):

        if not self.enabled:
            return

        self.report_lines.append(
            f"{label:<32} : {value}"
        )

    # --------------------------------------------------------

    def blank(self):

        if not self.enabled:
            return

        self.report_lines.append("")

    # --------------------------------------------------------
    # FUTURE PLACEHOLDERS
    # --------------------------------------------------------

    def export_svg(self, drawing, filename):

        if not self.enabled:
            return

        from svg_writer import write_debug_svg

        output = self.debug_folder / filename

        write_debug_svg(
            drawing,
            output,
        )

        self.info(f"Exported {filename}")

    def export_file(self, source, filename=None):

        if not self.enabled:
            return

        import shutil
        from pathlib import Path

        source = Path(source)

        if not source.exists():
            self.warning(f"Missing file: {source}")
            return

        if filename is None:
            filename = source.name

        shutil.copy2(
            source,
            self.debug_folder / filename,
        )

        self.info(f"Copied {filename}")

# ============================================================
# GLOBAL INSTANCE
# ============================================================

diag = Diagnostics()
