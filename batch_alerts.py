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

        output = folder / "Batch_Alerts.txt"

        with output.open(
            "w",
            encoding="utf-8",
        ) as f:

            f.write("=" * 60 + "\n")
            f.write("LaserPrep Batch Alerts\n")
            f.write("=" * 60 + "\n\n")

            # ------------------------------------------------
            # Aborts
            # ------------------------------------------------

            f.write("ABORTS\n")
            f.write("-" * 60 + "\n")

            if self.aborts:

                for project, pdf, message in self.aborts:

                    f.write(f"{project}\n")
                    f.write(f"    {pdf}\n")
                    f.write(f"    {message}\n\n")

            else:

                f.write("None\n\n")

            # ------------------------------------------------
            # Warnings
            # ------------------------------------------------

            f.write("WARNINGS\n")
            f.write("-" * 60 + "\n")

            if self.warnings:

                for project, pdf, message in self.warnings:

                    f.write(f"{project}\n")
                    f.write(f"    {pdf}\n")
                    f.write(f"    {message}\n\n")

            else:

                f.write("None\n")
