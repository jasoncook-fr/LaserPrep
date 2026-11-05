from batch_alerts import BatchAlerts


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

    report = (tmp_path / "CURRENT_BATCH_REPORT.txt").read_text(
        encoding="utf-8"
    )
    assert "EMAIL NOTIFICATION SUMMARY" in report
    assert "Emails sent successfully : 1" in report
    assert "Notifications pending    : 2" in report
    assert "MARTIN — No student email address found" in report
    assert "DUPONT — Email delivery failed: SMTP unavailable" in report

    history_reports = list((tmp_path / "BATCH_REPORTS").glob("*.txt"))
    assert len(history_reports) == 1
    assert history_reports[0].read_text(encoding="utf-8") == report


def test_report_explains_when_notifications_are_disabled(tmp_path):
    BatchAlerts().save(
        tmp_path,
        notification_summary={
            "status": "disabled",
            "sent": [],
            "pending": [],
        },
    )

    report = (tmp_path / "CURRENT_BATCH_REPORT.txt").read_text(
        encoding="utf-8"
    )
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

    report = (tmp_path / "CURRENT_BATCH_REPORT.txt").read_text(
        encoding="utf-8"
    )
    assert "Notification tracking was unavailable for this run." in report

