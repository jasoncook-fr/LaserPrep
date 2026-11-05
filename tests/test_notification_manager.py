import notification_manager
from notification_manager import NotificationManager


def create_project(tmp_path):
    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    project.mkdir(parents=True)
    (project / "drawing.pdf").write_bytes(b"test PDF content")
    return batch_root, project


def test_missing_recipient_is_recorded_as_pending(tmp_path):
    batch_root, project = create_project(tmp_path)
    manager = NotificationManager(tmp_path / "admin", batch_root, {})

    manager.queue(project, "COOK")
    manager.attempt(project, "COOK")

    summary = manager.get_run_summary()
    assert summary["status"] == "enabled"
    assert summary["sent"] == []
    assert summary["pending"] == [
        {
            "project": "COOK",
            "status": "pending",
            "detail": "No student email address found",
        }
    ]


def test_successful_delivery_is_recorded_as_sent(tmp_path, monkeypatch):
    batch_root, project = create_project(tmp_path)
    manager = NotificationManager(
        tmp_path / "admin", batch_root, {"COOK": "student@example.org"}
    )
    sent = []
    monkeypatch.setattr(
        notification_manager,
        "send_project_notification",
        lambda recipient, label: sent.append((recipient, label)),
    )

    manager.queue(project, "COOK")
    manager.attempt(project, "COOK")

    assert sent == [("student@example.org", "COOK")]
    summary = manager.get_run_summary()
    assert len(summary["sent"]) == 1
    assert summary["sent"][0]["project"] == "COOK"
    assert summary["pending"] == []


def test_delivery_exception_is_recorded_as_pending(tmp_path, monkeypatch):
    batch_root, project = create_project(tmp_path)
    manager = NotificationManager(
        tmp_path / "admin", batch_root, {"COOK": "student@example.org"}
    )

    def fail_delivery(recipient, label):
        raise RuntimeError("SMTP unavailable")

    monkeypatch.setattr(
        notification_manager,
        "send_project_notification",
        fail_delivery,
    )

    manager.queue(project, "COOK")
    manager.attempt(project, "COOK")

    summary = manager.get_run_summary()
    assert summary["sent"] == []
    assert summary["pending"] == [
        {
            "project": "COOK",
            "status": "pending",
            "detail": "Email delivery failed: SMTP unavailable",
        }
    ]

