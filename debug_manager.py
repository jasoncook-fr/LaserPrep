"""
debug_manager.py

LaserPrep
Debug Manager

Version 1.0

Creates and manages a complete debug session.

This class deliberately knows nothing about PDFs, SVG parsing,
or Drawings. It is only responsible for collecting debug files.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


class DebugManager:

    def __init__(self, enabled=False):

        self.enabled = enabled

        self.project_name = ""

        self.root = Path("debug")

        self.session = None

        self.log_file = None

    # ---------------------------------------------------------
    # Session
    # ---------------------------------------------------------

    def start_run(self, project_name: str):

        if not self.enabled:
            return

        self.project_name = project_name

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.session = self.root / f"{timestamp}_{project_name}"

        if self.session.exists():
            shutil.rmtree(self.session)

        self.session.mkdir(parents=True)

        self.log_file = self.session / "00_summary.txt"

        self.log(
            "==================================================\n"
            "LaserPrep Debug Session\n"
            "==================================================\n"
            f"Project : {project_name}\n"
            f"Started : {datetime.now()}\n\n"
        )

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------

    def log(self, text: str):

        if not self.enabled:
            return

        with open(
            self.log_file,
            "a",
            encoding="utf-8",
        ) as fp:

            fp.write(text)

            if not text.endswith("\n"):
                fp.write("\n")

    # ---------------------------------------------------------
    # Text report
    # ---------------------------------------------------------

    def save_text(self, filename: str, text: str):

        if not self.enabled:
            return

        file = self.session / filename

        file.write_text(
            text,
            encoding="utf-8",
        )

    # ---------------------------------------------------------
    # Copy existing file
    # ---------------------------------------------------------

    def copy_file(self, source, filename=None):

        if not self.enabled:
            return

        source = Path(source)

        if not source.exists():
            self.log(f"Missing file : {source}")
            return

        if filename is None:
            filename = source.name

        shutil.copy2(
            source,
            self.session / filename,
        )

    # ---------------------------------------------------------
    # SVG helper
    # ---------------------------------------------------------

    def save_svg(self, source, stage):

        """
        Copies an existing SVG into the debug folder.

        Example:

            save_svg(
                "temp/text.svg",
                "03_text.svg"
            )
        """

        self.copy_file(source, stage)

    # ---------------------------------------------------------
    # Generic file
    # ---------------------------------------------------------

    def save_file(self, source, stage):

        self.copy_file(source, stage)

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    def save_statistics(self, **kwargs):

        if not self.enabled:
            return

        report = []

        report.append(
            "=============================="
        )

        report.append(
            "Statistics"
        )

        report.append(
            "=============================="
        )

        for key, value in kwargs.items():

            report.append(
                f"{key:25} : {value}"
            )

        report.append("")

        self.log("\n".join(report))

    # ---------------------------------------------------------
    # Finish
    # ---------------------------------------------------------

    def finish(self):

        if not self.enabled:
            return

        self.log(
            "\n"
            "Finished : "
            f"{datetime.now()}\n"
        )

    # ---------------------------------------------------------
    # Convenience
    # ---------------------------------------------------------

    @property
    def folder(self):

        if not self.enabled:
            return None

        return self.session

    def exists(self):

        return (
            self.enabled
            and self.session is not None
            and self.session.exists()
        )
