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
            f"🟢 Accepted : {len(accepted)}\n",
            f"🟡 Warnings : {len(warnings)}\n",
            f"🔴 Rejected : {len(rejected)}\n",
            "\n",
        ]

        def append_grouped_section(title, emoji, results, detail_key=None):
            if not results:
                return

            lines.append(f"{emoji} {title}\n")
            lines.append("-" * 60 + "\n")

            grouped = {}
            for result in results:
                grouped.setdefault(result["project"], []).append(result)

            for project, project_results in grouped.items():
                lines.append(f"{project}\n")
                for result in project_results:
                    lines.append(f"  • {result['pdf']}\n")

                    if detail_key == "rejected":
                        for alert in result.get("alerts", []):
                            lines.append(f"    {alert}\n")
                        for warning in result.get("warnings", []):
                            lines.append(f"    • {warning}\n")
                    elif detail_key == "warnings":
                        for warning in result.get("warnings", []):
                            lines.append(f"    • {warning}\n")

                lines.append("\n")

        append_grouped_section("ACCEPTED", "✅", accepted)
        append_grouped_section("REJECTED", "❌", rejected, "rejected")
        append_grouped_section("WARNINGS", "⚠️", warnings, "warnings")

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
