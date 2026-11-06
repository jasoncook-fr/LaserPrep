
import batch_processing


def setup_scan_mocks(monkeypatch, previous_states=None, rejections=None):
    """Mock saved state and rejection history for batch scanning."""

    previous_states = previous_states or {}
    rejections = rejections or {}

    monkeypatch.setattr(
        batch_processing,
        "load_processing_state",
        lambda folder: previous_states.get(folder.name, {}),
    )

    monkeypatch.setattr(
        batch_processing,
        "load_recent_rejections",
        lambda retention_days: rejections,
    )

    monkeypatch.setattr(
        batch_processing,
        "pdf_hash",
        lambda path: path.read_text(encoding="utf-8"),
    )


def create_pdf(folder, name, content="test"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(content, encoding="utf-8")


# -------------------------------------------------------------------
# Batch scanning
# -------------------------------------------------------------------

def test_missing_batch_root_returns_empty_list(tmp_path, monkeypatch):
    setup_scan_mocks(monkeypatch)

    missing_root = tmp_path / "missing"

    assert batch_processing.scan_batch_changes(missing_root) == []


def test_empty_batch_root_returns_empty_list(tmp_path, monkeypatch):
    setup_scan_mocks(monkeypatch)

    batch_root = tmp_path / "STUDENTS"
    batch_root.mkdir()

    assert batch_processing.scan_batch_changes(batch_root) == []


def test_new_project_is_detected(tmp_path, monkeypatch):
    setup_scan_mocks(monkeypatch)

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    create_pdf(project, "drawing.pdf", "drawing data")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert changes == [
        {
            "project": "COOK",
            "kind": "new",
            "new": ["drawing.pdf"],
            "rejected": [],
            "changed": [],
            "removed": [],
        }
    ]


def test_new_pdf_in_existing_project_is_detected(tmp_path, monkeypatch):
    setup_scan_mocks(
        monkeypatch,
        previous_states={
            "COOK": {
                "existing.pdf": "existing data",
            }
        },
    )

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"

    create_pdf(project, "existing.pdf", "existing data")
    create_pdf(project, "new.pdf", "new data")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert changes == [
        {
            "project": "COOK",
            "kind": "updated",
            "new": ["new.pdf"],
            "rejected": [],
            "changed": [],
            "removed": [],
        }
    ]


def test_changed_pdf_is_detected(tmp_path, monkeypatch):
    setup_scan_mocks(
        monkeypatch,
        previous_states={
            "COOK": {
                "drawing.pdf": "old data",
            }
        },
    )

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    create_pdf(project, "drawing.pdf", "new data")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert changes == [
        {
            "project": "COOK",
            "kind": "updated",
            "new": [],
            "rejected": [],
            "changed": ["drawing.pdf"],
            "removed": [],
        }
    ]


def test_removed_pdf_is_detected(tmp_path, monkeypatch):
    setup_scan_mocks(
        monkeypatch,
        previous_states={
            "COOK": {
                "removed.pdf": "old data",
                "remaining.pdf": "remaining data",
            }
        },
    )

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    create_pdf(project, "remaining.pdf", "remaining data")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert changes == [
        {
            "project": "COOK",
            "kind": "updated",
            "new": [],
            "rejected": [],
            "changed": [],
            "removed": ["removed.pdf"],
        }
    ]


def test_nested_project_is_detected(tmp_path, monkeypatch):
    setup_scan_mocks(monkeypatch)

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK" / "PROJECT_A"
    create_pdf(project, "drawing.pdf", "drawing data")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert changes == [
        {
            "project": "COOK / PROJECT_A",
            "kind": "new",
            "new": ["drawing.pdf"],
            "rejected": [],
            "changed": [],
            "removed": [],
        }
    ]

def test_documents_folder_is_ignored_during_batch_scanning(
    tmp_path, monkeypatch
):
    setup_scan_mocks(monkeypatch)

    batch_root = tmp_path / "STUDENTS"
    student = batch_root / "COOK"

    create_pdf(
        student / "Documents",
        "Guide-Decoupe-Laser.pdf",
        "guide data",
    )
    create_pdf(
        student / "PROJECT_A",
        "drawing.pdf",
        "drawing data",
    )

    changes = batch_processing.scan_batch_changes(batch_root)

    assert [change["project"] for change in changes] == [
        "COOK / PROJECT_A"
    ]

def test_unchanged_project_is_not_reported(tmp_path, monkeypatch):
    setup_scan_mocks(
        monkeypatch,
        previous_states={
            "COOK": {
                "drawing.pdf": "drawing data",
            }
        },
    )

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    create_pdf(project, "drawing.pdf", "drawing data")

    assert batch_processing.scan_batch_changes(batch_root) == []


def test_recently_rejected_pdf_is_reported(tmp_path, monkeypatch):
    setup_scan_mocks(
        monkeypatch,
        rejections={
            "COOK": {"drawing.pdf"},
        },
    )

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    create_pdf(project, "drawing.pdf", "drawing data")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert changes == [
        {
            "project": "COOK",
            "kind": "updated",
            "new": [],
            "rejected": ["drawing.pdf"],
            "changed": [],
            "removed": [],
        }
    ]


def test_modified_rejected_pdf_is_reported_as_changed(tmp_path, monkeypatch):
    setup_scan_mocks(
        monkeypatch,
        previous_states={
            "COOK": {
                "drawing.pdf": "old data",
            }
        },
        rejections={
            "COOK": {"drawing.pdf"},
        },
    )

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    create_pdf(project, "drawing.pdf", "new data")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert changes == [
        {
            "project": "COOK",
            "kind": "updated",
            "new": [],
            "rejected": [],
            "changed": ["drawing.pdf"],
            "removed": [],
        }
    ]


def test_multiple_projects_are_sorted(tmp_path, monkeypatch):
    setup_scan_mocks(monkeypatch)

    batch_root = tmp_path / "STUDENTS"

    create_pdf(batch_root / "ZEBRA", "z.pdf")
    create_pdf(batch_root / "ADAMS", "a.pdf")
    create_pdf(batch_root / "COOK", "c.pdf")

    changes = batch_processing.scan_batch_changes(batch_root)

    assert [change["project"] for change in changes] == [
        "ADAMS",
        "COOK",
        "ZEBRA",
    ]

# -------------------------------------------------------------------
# Student documents
# -------------------------------------------------------------------

def test_prepare_student_documents_creates_folder_and_copies_guide(
    tmp_path, monkeypatch
):
    batch_root = tmp_path / "STUDENTS"
    student = batch_root / "COOK"
    student.mkdir(parents=True)

    master_guide = tmp_path / "RESOURCES" / "Guide-Decoupe-Laser.pdf"
    master_guide.parent.mkdir()
    master_guide.write_text("guide content", encoding="utf-8")

    monkeypatch.setattr(
        batch_processing,
        "STUDENT_GUIDE",
        master_guide,
    )

    messages = []
    warnings = []

    batch_processing.prepare_student_documents(
        batch_root,
        messages.append,
        warnings.append,
    )

    student_guide = (
        student
        / batch_processing.STUDENT_DOCUMENTS_FOLDER
        / master_guide.name
    )

    assert student_guide.is_file()
    assert student_guide.read_text(encoding="utf-8") == "guide content"
    assert warnings == []


def test_prepare_student_documents_does_not_overwrite_existing_guide(
    tmp_path, monkeypatch
):
    batch_root = tmp_path / "STUDENTS"
    student = batch_root / "COOK"
    documents = student / "Documents"
    documents.mkdir(parents=True)

    master_guide = tmp_path / "RESOURCES" / "Guide-Decoupe-Laser.pdf"
    master_guide.parent.mkdir()
    master_guide.write_text("updated master guide", encoding="utf-8")

    student_guide = documents / master_guide.name
    student_guide.write_text("existing student guide", encoding="utf-8")

    monkeypatch.setattr(
        batch_processing,
        "STUDENT_GUIDE",
        master_guide,
    )

    batch_processing.prepare_student_documents(
        batch_root,
        lambda message: None,
        lambda message: None,
    )

    assert student_guide.read_text(encoding="utf-8") == (
        "existing student guide"
    )

# -------------------------------------------------------------------
# Batch orchestration
# -------------------------------------------------------------------

def setup_process_batch_mocks(monkeypatch):
    """Disable external services and capture batch orchestration."""

    messages = []
    processed = []
    notification_events = []

    class FakeAlerts:
        def save(self, admin_root, retention_days, notification_summary=None):
            pass

    class FakeNotifications:
        def __init__(self, admin_root, batch_root, student_emails):
            notification_events.append(("initialized", student_emails))

        def queue(self, folder, project_name):
            notification_events.append(("queue", project_name))

        def attempt(self, folder, student_folder_name):
            notification_events.append(("attempt", student_folder_name))

        def clear(self, folder):
            notification_events.append(("clear", folder.name))

        def record_pending(self, project_name, detail):
            notification_events.append(("pending", project_name, detail))

        def get_run_summary(self):
            return {
                "status": "enabled",
                "sent": [],
                "pending": [],
            }

    monkeypatch.setattr(batch_processing, "BatchAlerts", FakeAlerts)
    monkeypatch.setattr(
        batch_processing,
        "NotificationManager",
        FakeNotifications,
    )
    monkeypatch.setattr(
        batch_processing,
        "get_student_emails",
        lambda: {},
    )

    def process_project(folder, alerts, **kwargs):
        processed.append((folder, kwargs))
        return "completed"

    return messages, processed, notification_events, process_project


def test_process_batch_missing_root(tmp_path, monkeypatch):
    messages, processed, events, process_project = (
        setup_process_batch_mocks(monkeypatch)
    )

    errors = []

    batch_processing.process_batch(
        tmp_path / "missing",
        process_project,
        errors.append,
        messages.append,
        messages.append,
        send_notifications=False,
    )

    assert errors == [f"Batch root does not exist: {tmp_path / 'missing'}"]
    assert processed == []


def test_process_batch_empty_root(tmp_path, monkeypatch, capsys):
    messages, processed, events, process_project = (
        setup_process_batch_mocks(monkeypatch)
    )

    batch_root = tmp_path / "STUDENTS"
    batch_root.mkdir()

    batch_processing.process_batch(
        batch_root,
        process_project,
        messages.append,
        messages.append,
        messages.append,
        send_notifications=False,
    )

    assert processed == []
    assert "No projects found." in capsys.readouterr().out


def test_process_batch_processes_project(tmp_path, monkeypatch):
    messages, processed, events, process_project = (
        setup_process_batch_mocks(monkeypatch)
    )

    batch_root = tmp_path / "STUDENTS"
    project = batch_root / "COOK"
    create_pdf(project, "drawing.pdf")

    batch_processing.process_batch(
        batch_root,
        process_project,
        messages.append,
        messages.append,
        messages.append,
        send_notifications=False,
    )

    assert len(processed) == 1
    assert processed[0][0] == project
    assert processed[0][1]["use_state"] is True
    assert processed[0][1]["batch_project_name"] == "COOK"
    assert processed[0][1]["progress_label"] == "Project 1 / 1"


def test_process_batch_counts_skipped_projects(tmp_path, monkeypatch):
    messages, processed, events, _ = setup_process_batch_mocks(monkeypatch)

    batch_root = tmp_path / "STUDENTS"
    create_pdf(batch_root / "ADAMS", "a.pdf")
    create_pdf(batch_root / "COOK", "c.pdf")

    results = iter(["skipped", "completed"])

    def process_project(folder, alerts, **kwargs):
        processed.append(folder)
        return next(results)

    batch_processing.process_batch(
        batch_root,
        process_project,
        messages.append,
        messages.append,
        messages.append,
        send_notifications=False,
    )

    assert len(processed) == 2
    assert any("Projects found     : 2" in msg for msg in messages)
    assert any("Projects processed : 1" in msg for msg in messages)
    assert any("Projects skipped   : 1" in msg for msg in messages)


def test_process_batch_notifications_disabled(tmp_path, monkeypatch):
    messages, processed, events, process_project = (
        setup_process_batch_mocks(monkeypatch)
    )

    batch_root = tmp_path / "STUDENTS"
    create_pdf(batch_root / "COOK", "drawing.pdf")

    batch_processing.process_batch(
        batch_root,
        process_project,
        messages.append,
        messages.append,
        messages.append,
        send_notifications=False,
    )

    assert events == []
    assert any(
        "Email notifications are disabled" in msg
        for msg in messages
    )


def test_process_batch_notification_queue_and_attempt(tmp_path, monkeypatch):
    messages, processed, events, process_project = (
        setup_process_batch_mocks(monkeypatch)
    )

    batch_root = tmp_path / "STUDENTS"
    create_pdf(batch_root / "COOK", "drawing.pdf")

    batch_processing.process_batch(
        batch_root,
        process_project,
        messages.append,
        messages.append,
        messages.append,
        send_notifications=True,
    )

    assert ("initialized", {}) in events
    assert ("queue", "COOK") in events
    assert ("attempt", "COOK") in events


def test_process_batch_notification_lookup_failure(tmp_path, monkeypatch):
    messages, processed, events, process_project = (
        setup_process_batch_mocks(monkeypatch)
    )

    def fail_lookup():
        raise RuntimeError("Nextcloud unavailable")

    monkeypatch.setattr(
        batch_processing,
        "get_student_emails",
        fail_lookup,
    )

    batch_root = tmp_path / "STUDENTS"
    create_pdf(batch_root / "COOK", "drawing.pdf")

    batch_processing.process_batch(
        batch_root,
        process_project,
        messages.append,
        messages.append,
        messages.append,
        send_notifications=True,
    )

    assert len(processed) == 1
    assert any(
        "Email notifications will be deferred" in msg
        for msg in messages
    )


def test_process_batch_notification_failure_does_not_stop_processing(
    tmp_path, monkeypatch
):
    messages, processed, events, process_project = (
        setup_process_batch_mocks(monkeypatch)
    )

    class BrokenNotifications:
        def __init__(self, *args):
            pass

        def queue(self, *args):
            raise RuntimeError("Notification failure")

        def attempt(self, *args):
            pass

        def clear(self, *args):
            pass

        def record_pending(self, *args):
            pass

        def get_run_summary(self):
            return {
                "status": "enabled",
                "sent": [],
                "pending": [],
            }

    monkeypatch.setattr(
        batch_processing,
        "NotificationManager",
        BrokenNotifications,
    )

    batch_root = tmp_path / "STUDENTS"
    create_pdf(batch_root / "COOK", "drawing.pdf")

    batch_processing.process_batch(
        batch_root,
        process_project,
        messages.append,
        messages.append,
        messages.append,
        send_notifications=True,
    )

    assert len(processed) == 1
    assert any(
        "Notification handling failed" in msg
        for msg in messages
    )

