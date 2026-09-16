"""Batch-level administrative reporting.

The individual Report is the source of truth. This class receives the final
result for each PDF and presents only operator-relevant information.

Version 1.1
"""


class BatchAlerts:
    def __init__(self):
        self.results = []

    def result(self, project: str, pdf: str, report_entry: dict) -> None:
        """Record a snapshot of the final Report result for one PDF."""
        self.results.append(
            {
                "project": project,
                "pdf": pdf,
                "status": report_entry.get("status", "PASS"),
                "warnings": list(report_entry.get("warnings", [])),
                "alerts": list(report_entry.get("alerts", [])),
            }
        )

    def save(self, folder) -> None:
        rejected = [
            r for r in self.results if r["status"] == "REJECTED"
        ]
        warnings = [
            r for r in self.results if r["status"] == "WARNING"
        ]
        accepted = [
            r for r in self.results if r["status"] == "PASS"
        ]

        lines = [
            "=" * 60 + "\n",
            "LaserPrep Batch Report\n",
            "=" * 60 + "\n\n",
            "SUMMARY\n",
            "-" * 60 + "\n",
            f"Accepted : {len(accepted)}\n",
            f"Warnings : {len(warnings)}\n",
            f"Rejected : {len(rejected)}\n",
            "\n",
            "❌ REJECTED\n",
            "-" * 60 + "\n",
        ]

        if rejected:
            for result in rejected:
                lines.append(f"{result['project']}\n")
                lines.append(f"    {result['pdf']}\n")

                for message in result["alerts"]:
                    for line in str(message).splitlines():
                        lines.append(f"    {line}\n")

                # Keep any additional warnings visible on a rejected file.
                for message in result["warnings"]:
                    for line in str(message).splitlines():
                        lines.append(f"    ⚠️ {line}\n")

                lines.append("\n")
        else:
            lines.append("None\n\n")

        lines.extend([
            "⚠️ WARNINGS\n",
            "-" * 60 + "\n",
        ])

        if warnings:
            for result in warnings:
                lines.append(f"{result['project']}\n")
                lines.append(f"    {result['pdf']}\n")

                for message in result["warnings"]:
                    for line in str(message).splitlines():
                        lines.append(f"    • {line}\n")

                lines.append("\n")
        else:
            lines.append("None\n")

        report = "".join(lines)

        folder.mkdir(parents=True, exist_ok=True)

        history_folder = folder / "BATCH_REPORTS"
        history_folder.mkdir(parents=True, exist_ok=True)

        current_report = folder / "CURRENT_BATCH_REPORT.txt"
        current_report.write_text(report, encoding="utf-8")

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        historical_report = history_folder / f"{timestamp}.txt"
        historical_report.write_text(report, encoding="utf-8")
