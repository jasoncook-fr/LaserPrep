"""Rolling administrative activity report for LaserPrep.

Only actual processing refreshes a PDF's activity timestamp. Cached or skipped
PDFs remain in the rolling report with their original processing date.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path


class BatchAlerts:
    def __init__(self):
        self.results = []

    def result(self, project: str, pdf: str, report_entry: dict) -> None:
        """Record a result produced by actual PDF processing."""
        self.results.append({
            "project": project,
            "pdf": pdf,
            "status": report_entry.get("status", "PASS"),
            "warnings": list(report_entry.get("warnings", [])),
            "alerts": list(report_entry.get("alerts", [])),
            "processed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        })

    @staticmethod
    def _load_activity(path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            return [
                item for item in data["entries"]
                if isinstance(item, dict)
                and isinstance(item.get("project"), str)
                and isinstance(item.get("pdf"), str)
                and isinstance(item.get("processed_at"), str)
            ]
        return []

    @staticmethod
    def _parse_timestamp(value: str):
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    def save(self, folder: Path, retention_days: int = 7) -> None:
        """Update the rolling activity log and write current + history reports."""
        folder.mkdir(parents=True, exist_ok=True)
        activity_dir = folder / "activity"
        activity_dir.mkdir(parents=True, exist_ok=True)

        activity_path = activity_dir / "BATCH_ACTIVITY.json"
        history_folder = folder / "BATCH_REPORTS"
        history_folder.mkdir(parents=True, exist_ok=True)

        retention_days = max(1, int(retention_days))
        now = datetime.now().astimezone()
        cutoff = now - timedelta(days=retention_days)

        activity = {
            (entry["project"], entry["pdf"]): entry
            for entry in self._load_activity(activity_path)
        }
        latest_run = list(self.results)
        for entry in latest_run:
            activity[(entry["project"], entry["pdf"])] = entry

        recent_entries = []
        for entry in activity.values():
            processed_at = self._parse_timestamp(entry.get("processed_at"))
            if processed_at is None:
                continue
            if processed_at.tzinfo is None:
                processed_at = processed_at.astimezone()
            if processed_at >= cutoff:
                recent_entries.append(entry)

        recent_entries.sort(key=lambda item: item["processed_at"], reverse=True)

        payload = {
            "version": 1,
            "retention_days": retention_days,
            "entries": recent_entries,
        }
        tmp_path = activity_path.with_suffix(activity_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(activity_path)

        latest_by_project = {}
        for entry in latest_run:
            current = latest_by_project.get(entry["project"])
            if current is None or entry["processed_at"] > current["processed_at"]:
                latest_by_project[entry["project"]] = entry

        latest_project = max(
            latest_by_project.values(),
            key=lambda item: item["processed_at"],
            default=None,
        )
        latest_project_name = latest_project["project"] if latest_project else None

        lines = [
            "=" * 60 + "\n",
            "LaserPrep Batch Report\n",
            "=" * 60 + "\n",
            f"Rolling activity window: {retention_days} days\n",
            f"Report generated: {now.strftime('%d %b %Y · %H:%M')}\n\n",
            "LAST PROCESSED FILES\n",
            "-" * 60 + "\n",
        ]

        if latest_by_project:
            for project, newest in sorted(
                latest_by_project.items(),
                key=lambda pair: pair[1]["processed_at"],
                reverse=True,
            ):
                processed_at = self._parse_timestamp(newest["processed_at"])
                stamp = processed_at.astimezone().strftime("%d %b %Y · %H:%M")
                marker = "  [LATEST]" if project == latest_project_name else ""
                lines.append(f"{project}{marker}\n")
                lines.append(f"  🕒 {stamp}\n")
                for entry in latest_run:
                    if entry["project"] == project:
                        lines.append(f"  • {entry['pdf']}\n")
                lines.append("\n")
        else:
            lines.append("No files processed in this batch run.\n\n")

        rejected = [r for r in recent_entries if r.get("status") == "REJECTED"]
        warnings = [r for r in recent_entries if r.get("status") == "WARNING"]
        accepted = [r for r in recent_entries if r.get("status") == "PASS"]

        lines.extend([
            f"SUMMARY — LAST {retention_days} DAYS\n",
            "-" * 60 + "\n",
            f"🟢 Accepted : {len(accepted)}\n",
            f"🟡 Warnings : {len(warnings)}\n",
            f"🔴 Rejected : {len(rejected)}\n\n",
        ])

        def append_grouped_section(title, emoji, results, detail_key=None):
            if not results:
                return
            lines.append(f"{emoji} {title}\n")
            lines.append("-" * 60 + "\n")
            grouped = {}
            for result in results:
                grouped.setdefault(result["project"], []).append(result)

            projects = sorted(
                grouped,
                key=lambda name: max(
                    item["processed_at"] for item in grouped[name]
                ),
                reverse=True,
            )
            for project in projects:
                project_results = sorted(
                    grouped[project],
                    key=lambda item: item["processed_at"],
                    reverse=True,
                )
                newest = self._parse_timestamp(project_results[0]["processed_at"])
                stamp = newest.astimezone().strftime("%d %b %Y · %H:%M")
                lines.append(f"{project}\n")
                lines.append(f"  🕒 {stamp}\n")
                if detail_key == "warnings":
                    overlap_files = []
                    other_warnings = []

                    for result in project_results:
                        for warning in result.get("warnings", []):
                            match = re.search(
                                r"Potential geometry overlap:\s*(\d+)\s+groups? detected",
                                warning,
                                re.IGNORECASE,
                            )
                            if match:
                                overlap_files.append((result["pdf"], int(match.group(1))))
                            else:
                                other_warnings.append((result["pdf"], warning))

                    for filename, group_count in overlap_files:
                        lines.append(f"  • {filename} — {group_count} groups\n")

                    if overlap_files:
                        file_word = "file" if len(overlap_files) == 1 else "files"
                        lines.append(
                            f"  Potential geometry overlap detected in "
                            f"{len(overlap_files)} {file_word}.\n"
                        )

                    for filename, warning in other_warnings:
                        lines.append(f"  • {filename}\n")
                        lines.append(f"    • {warning}\n")

                else:
                    for result in project_results:
                        lines.append(f"  • {result['pdf']}\n")
                        if detail_key == "rejected":
                            for alert in result.get("alerts", []):
                                lines.append(f"    {alert}\n")
                            for warning in result.get("warnings", []):
                                lines.append(f"    • {warning}\n")
                lines.append("\n")

        append_grouped_section("ACCEPTED", "✅", accepted)
        append_grouped_section("REJECTED", "❌", rejected, "rejected")
        append_grouped_section("WARNINGS", "⚠️", warnings, "warnings")

        report = "".join(lines)
        (folder / "CURRENT_BATCH_REPORT.txt").write_text(report, encoding="utf-8")

        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        (history_folder / f"{timestamp}.txt").write_text(report, encoding="utf-8")
