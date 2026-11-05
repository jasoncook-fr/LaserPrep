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

    def save(
        self, folder: Path, retention_days: int = 7,
        notification_summary: dict | None = None,
    ) -> None:
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

        from xml.sax.saxutils import escape

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        notification_summary = notification_summary or {
            "status": "unavailable",
            "sent": [],
            "pending": [],
        }
        notification_status = notification_summary.get("status", "unavailable")
        sent = notification_summary.get("sent", [])
        pending = notification_summary.get("pending", [])

        report_path = folder / "CURRENT_BATCH_REPORT.pdf"
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        history_path = history_folder / f"{timestamp}.pdf"

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#202936"),
            spaceAfter=2 * mm,
        ))
        styles.add(ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#667085"),
            spaceAfter=5 * mm,
        ))
        styles.add(ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#263445"),
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ))
        styles.add(ParagraphStyle(
            name="ProjectHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#344054"),
            spaceBefore=2.5 * mm,
            spaceAfter=1 * mm,
            keepWithNext=True,
        ))
        styles.add(ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#344054"),
            spaceAfter=1 * mm,
        ))
        styles.add(ParagraphStyle(
            name="ReportSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#667085"),
        ))
        styles.add(ParagraphStyle(
            name="ReportBullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            leftIndent=4 * mm,
            firstLineIndent=-2.5 * mm,
            textColor=colors.HexColor("#344054"),
            spaceAfter=0.7 * mm,
        ))
        styles.add(ParagraphStyle(
            name="ReportStatus",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#344054"),
        ))

        story = [
            Paragraph("LaserPrep Batch Report", styles["ReportTitle"]),
            Paragraph(
                f"Generated {escape(now.strftime('%d %b %Y at %H:%M'))}"
                f" &nbsp;&nbsp;|&nbsp;&nbsp; Rolling activity window: "
                f"{retention_days} days",
                styles["ReportSubtitle"],
            ),
        ]

        def add_section(title):
            story.append(Paragraph(escape(title), styles["SectionHeading"]))

        def add_bullet(text):
            story.append(Paragraph(
                f"&bull;&nbsp; {text}",
                styles["ReportBullet"],
            ))

        # Email notification summary
        add_section("Email notifications")
        if notification_status == "disabled":
            notification_text = "Email notifications were disabled for this run."
            notification_fill = colors.HexColor("#F2F4F7")
        elif notification_status == "unavailable":
            notification_text = "Notification tracking was unavailable for this run."
            notification_fill = colors.HexColor("#FFF4E5")
        else:
            notification_text = (
                f"Emails sent successfully: <b>{len(sent)}</b>"
                f"&nbsp;&nbsp;&nbsp; Notifications pending: <b>{len(pending)}</b>"
            )
            notification_fill = colors.HexColor("#F2F7F4")

        notification_rows = [[
            Paragraph( notification_text, styles["ReportStatus"])
        ]]
        notification_table = Table(notification_rows, colWidths=[170 * mm])
        notification_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), notification_fill),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5DD")),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ]))
        story.append(notification_table)

        if notification_status == "enabled" and pending:
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph("Pending notifications", styles["ProjectHeading"]))
            for item in pending:
                project = escape(str(item.get("project", "Unknown project")))
                detail = escape(str(item.get("detail", "")))
                text = f"<b>{project}</b>"
                if detail:
                    text += f" — {detail}"
                add_bullet(text)

        # Latest processed files in this run
        add_section("Latest processed files")
        if latest_by_project:
            for project, newest in sorted(
                latest_by_project.items(),
                key=lambda pair: pair[1]["processed_at"],
                reverse=True,
            ):
                processed_at = self._parse_timestamp(newest["processed_at"])
                stamp = processed_at.astimezone().strftime("%d %b %Y at %H:%M")
                label = "  (latest project)" if project == latest_project_name else ""
                group = [
                    Paragraph(
                        f"{escape(project)}"
                        f"<font color='#667085'>{escape(label)}</font>",
                        styles["ProjectHeading"],
                    ),
                    Paragraph(f"Processed: {escape(stamp)}", styles["ReportSmall"]),
                ]
                for entry in latest_run:
                    if entry["project"] == project:
                        group.append(Paragraph(
                            f"&bull;&nbsp; {escape(entry['pdf'])}",
                            styles["ReportBullet"],
                        ))
                story.extend(group)
        else:
            story.append(Paragraph(
                "No files processed in this batch run.",
                styles["ReportBody"],
            ))

        # Rolling activity summary
        rejected = [r for r in recent_entries if r.get("status") == "REJECTED"]
        warnings = [r for r in recent_entries if r.get("status") == "WARNING"]
        accepted = [r for r in recent_entries if r.get("status") == "PASS"]

        add_section(f"Summary — last {retention_days} days")
        summary_data = [[
            Paragraph("<b>Result</b>", styles["ReportBody"]),
            Paragraph("<b>Files</b>", styles["ReportBody"]),
        ]]
        for label, results in (
            ("Accepted", accepted),
            ("Warnings", warnings),
            ("Rejected", rejected),
        ):
            summary_data.append([
                Paragraph(escape(label), styles["ReportBody"]),
                Paragraph(str(len(results)), styles["ReportBody"]),
            ])
        summary_table = Table(summary_data, colWidths=[145 * mm, 25 * mm])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAECF0")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ]))
        story.append(summary_table)

        def append_grouped_section(title, results, detail_key=None):
            if not results:
                return

            add_section(title)
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
                stamp = newest.astimezone().strftime("%d %b %Y at %H:%M")
                group = [Paragraph(
                    f"{escape(project)}"
                    f"<font color='#667085'> — {escape(stamp)}</font>",
                    styles["ProjectHeading"],
                )]

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
                        group.append(Paragraph(
                            f"&bull;&nbsp; {escape(filename)} — "
                            f"{group_count} overlap groups",
                            styles["ReportBullet"],
                        ))

                    if overlap_files:
                        file_word = "file" if len(overlap_files) == 1 else "files"
                        group.append(Paragraph(
                            f"Potential geometry overlap detected in "
                            f"{len(overlap_files)} {file_word}.",
                            styles["ReportSmall"],
                        ))

                    for filename, warning in other_warnings:
                        group.append(Paragraph(
                            f"&bull;&nbsp; {escape(filename)}",
                            styles["ReportBullet"],
                        ))
                        group.append(Paragraph(
                            f"&nbsp;&nbsp;&nbsp; {escape(warning)}",
                            styles["ReportSmall"],
                        ))
                else:
                    for result in project_results:
                        group.append(Paragraph(
                            f"&bull;&nbsp; {escape(result['pdf'])}",
                            styles["ReportBullet"],
                        ))
                        if detail_key == "rejected":
                            for alert in result.get("alerts", []):
                                group.append(Paragraph(
                                    f"&nbsp;&nbsp;&nbsp; {escape(str(alert))}",
                                    styles["ReportSmall"],
                                ))
                            for warning in result.get("warnings", []):
                                group.append(Paragraph(
                                    f"&nbsp;&nbsp;&nbsp; Warning: "
                                    f"{escape(str(warning))}",
                                    styles["ReportSmall"],
                                ))
                story.extend(group)

        append_grouped_section("Accepted", accepted)
        append_grouped_section("Rejected", rejected, "rejected")
        append_grouped_section("Warnings", warnings, "warnings")

        def draw_footer(canvas, document):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#D0D5DD"))
            canvas.setLineWidth(0.4)
            canvas.line(20 * mm, 14 * mm, 190 * mm, 14 * mm)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#667085"))
            canvas.drawString(20 * mm, 9 * mm, "LaserPrep — Administrative report")
            canvas.drawRightString(
                190 * mm, 9 * mm, f"Page {document.page}"
            )
            canvas.restoreState()

        def write_pdf(path):
            document = SimpleDocTemplate(
                str(path),
                pagesize=A4,
                rightMargin=20 * mm,
                leftMargin=20 * mm,
                topMargin=17 * mm,
                bottomMargin=21 * mm,
                title="LaserPrep Batch Report",
                author="LaserPrep",
            )
            document.build(
                story,
                onFirstPage=draw_footer,
                onLaterPages=draw_footer,
            )

        write_pdf(report_path)
        history_path.write_bytes(report_path.read_bytes())
