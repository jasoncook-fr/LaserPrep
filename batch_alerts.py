"""
batch_alerts.py

Collect important warnings and aborts produced during
Batch Mode processing.

Version 1.0
"""


class BatchAlerts:

    def __init__(self):
        self.aborts = []
        self.warnings = []

    # ========================================================
    # Public API
    # ========================================================

    def abort(
        self,
        project: str,
        pdf: str,
        message: str,
    ) -> None:
        self.aborts.append(
            (project, pdf, message)
        )

    def warning(
        self,
        project: str,
        pdf: str,
        message: str,
    ) -> None:
        self.warnings.append(
            (project, pdf, message)
        )

    # ========================================================
    # Save
    # ========================================================

    def save(self, folder) -> None:

        report_lines = []

        report_lines.append("=" * 60 + "\n")
        report_lines.append("LaserPrep Batch Report\n")
        report_lines.append("=" * 60 + "\n\n")

        # ------------------------------------------------
        # Aborts
        # ------------------------------------------------

        report_lines.append("ABORTS\n")
        report_lines.append("-" * 60 + "\n")

        if self.aborts:

            for project, pdf, message in self.aborts:
                report_lines.append(f"{project}\n")
                report_lines.append(f"    {pdf}\n")
                report_lines.append(f"    {message}\n\n")

        else:

            report_lines.append("None\n\n")

        # ------------------------------------------------
        # Warnings
        # ------------------------------------------------

        report_lines.append("WARNINGS\n")
        report_lines.append("-" * 60 + "\n")

        if self.warnings:

            for project, pdf, message in self.warnings:
                report_lines.append(f"{project}\n")
                report_lines.append(f"    {pdf}\n")
                report_lines.append(f"    {message}\n\n")

        else:

            report_lines.append("None\n")

        report = "".join(report_lines)

        # ------------------------------------------------
        # Administrative report directories
        # ------------------------------------------------

        folder.mkdir(parents=True, exist_ok=True)

        history_folder = folder / "BATCH_REPORTS"
        history_folder.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------
        # Current report
        # ------------------------------------------------

        current_report = folder / "CURRENT_BATCH_REPORT.txt"

        with current_report.open(
            "w",
            encoding="utf-8",
        ) as f:
            f.write(report)

        # ------------------------------------------------
        # Historical report
        # ------------------------------------------------

        from datetime import datetime

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        historical_report = (
            history_folder / f"{timestamp}.txt"
        )

        with historical_report.open(
            "w",
            encoding="utf-8",
        ) as f:
            f.write(report)
