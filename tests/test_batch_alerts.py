import fitz

from batch_alerts import BatchAlerts


def read_report_text(path):
    with fitz.open(path) as document:
        return "\\n".join(page.get_text() for page in document)


def test_report_includes_notification_summary_in_current_and_history_reports(
    tmp_path,
):
    summary = {
        "status": "enabled",
        "sent": [
            {"project": "COOK", "status": "sent", "detail": ""},
        ],
        "pending": [
            {
                "project": "MARTIN",
                "status": "pending",
                "detail": "No student email address found",
            },
            {
                "project": "DUPONT",
                "status": "pending",
                "detail": "Email delivery failed: SMTP unavailable",
            },
        ],
    }

    BatchAlerts().save(tmp_path, notification_summary=summary)

    report_path = tmp_path / "CURRENT_BATCH_REPORT.pdf"
    assert report_path.is_file()
    report = read_report_text(report_path)
    assert "Email notifications" in report
    assert "Emails sent successfully: 1" in report
    assert "Notifications pending: 2" in report
    assert "MARTIN" in report
    assert "No student email address found" in report
    assert "DUPONT" in report
    assert "Email delivery failed: SMTP unavailable" in report

    history_reports = list((tmp_path / "BATCH_REPORTS").glob("*.pdf"))
    assert len(history_reports) == 1
    assert read_report_text(history_reports[0]) == report


def test_report_explains_when_notifications_are_disabled(tmp_path):
    BatchAlerts().save(
        tmp_path,
        notification_summary={
            "status": "disabled",
            "sent": [],
            "pending": [],
        },
    )

    report = read_report_text(tmp_path / "CURRENT_BATCH_REPORT.pdf")
    assert "Email notifications were disabled for this run." in report


def test_report_explains_when_notification_tracking_is_unavailable(tmp_path):
    BatchAlerts().save(
        tmp_path,
        notification_summary={
            "status": "unavailable",
            "sent": [],
            "pending": [],
        },
    )

    report = read_report_text(tmp_path / "CURRENT_BATCH_REPORT.pdf")
    assert "Notification tracking was unavailable for this run." in report
