
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import processing_state


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """Redirect all processing-state paths to temporary directories."""

    admin_root = tmp_path / "ADMIN"
    batch_root = tmp_path / "STUDENTS"

    monkeypatch.setattr(processing_state, "ADMIN_ROOT", admin_root)
    monkeypatch.setattr(processing_state, "BATCH_ROOT", batch_root)

    return admin_root, batch_root


@pytest.fixture
def project(isolated_paths):
    _, batch_root = isolated_paths
    folder = batch_root / "COOK"
    folder.mkdir(parents=True)
    return folder


# -------------------------------------------------------------------
# PDF hashing
# -------------------------------------------------------------------

def test_pdf_hash_returns_sha256(tmp_path):
    pdf = tmp_path / "example.pdf"
    content = b"LaserPrep test PDF content"
    pdf.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()

    assert processing_state.pdf_hash(pdf) == expected


def test_pdf_hash_missing_file_raises_error(tmp_path):
    missing_pdf = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        processing_state.pdf_hash(missing_pdf)


# -------------------------------------------------------------------
# Processing-state file paths
# -------------------------------------------------------------------

def test_processing_state_path_for_batch_project(isolated_paths):
    admin_root, batch_root = isolated_paths
    folder = batch_root / "COOK"

    result = processing_state.processing_state_path(folder)

    assert result == admin_root / "state" / "COOK.json"
    assert result.parent.is_dir()


def test_processing_state_path_for_individual_project(isolated_paths):
    admin_root, batch_root = isolated_paths
    folder = batch_root / "2026" / "COOK"

    result = processing_state.processing_state_path(folder)

    assert result == admin_root / "state" / "2026__COOK.json"


# -------------------------------------------------------------------
# Saving and loading processing records
# -------------------------------------------------------------------

def test_save_and_load_processing_records(project):
    records = {
        "drawing.pdf": {
            "hash": "abc123",
            "status": "ACCEPTED",
        },
        "another.pdf": {
            "hash": "def456",
            "status": "REJECTED",
        },
    }

    processing_state.save_processing_state(project, records)

    loaded = processing_state.load_processing_records(project)

    assert loaded == records


def test_saved_state_uses_version_2_format(project):
    records = {
        "drawing.pdf": {
            "hash": "abc123",
            "status": "ACCEPTED",
        }
    }

    processing_state.save_processing_state(project, records)

    state_file = processing_state.processing_state_path(project)
    data = json.loads(state_file.read_text(encoding="utf-8"))

    assert data["version"] == 2
    assert data["files"] == records


def test_missing_state_file_returns_empty_records(project):
    assert processing_state.load_processing_records(project) == {}


@pytest.mark.parametrize(
    "content",
    [
        "{invalid json",
        "",
        "[]",
        '"not a dictionary"',
        "null",
    ],
)
def test_invalid_state_file_returns_empty_records(project, content):
    state_file = processing_state.processing_state_path(project)
    state_file.write_text(content, encoding="utf-8")

    assert processing_state.load_processing_records(project) == {}


# -------------------------------------------------------------------
# Legacy state compatibility
# -------------------------------------------------------------------

def test_legacy_state_format_is_supported(project):
    legacy_data = {
        "drawing.pdf": "abc123",
        "another.pdf": "def456",
    }

    state_file = processing_state.processing_state_path(project)
    state_file.write_text(
        json.dumps(legacy_data),
        encoding="utf-8",
    )

    expected = {
        "drawing.pdf": {"hash": "abc123", "status": None},
        "another.pdf": {"hash": "def456", "status": None},
    }

    assert processing_state.load_processing_records(project) == expected


# -------------------------------------------------------------------
# Invalid record filtering
# -------------------------------------------------------------------

def test_invalid_records_are_ignored(project):
    data = {
        "files": {
            "valid.pdf": {"hash": "abc123", "status": "ACCEPTED"},
            "missing_hash.pdf": {"status": "ACCEPTED"},
            "non_string_hash.pdf": {"hash": 123},
            "not_a_record.pdf": "abc123",
        }
    }

    state_file = processing_state.processing_state_path(project)
    state_file.write_text(json.dumps(data), encoding="utf-8")

    assert processing_state.load_processing_records(project) == {
        "valid.pdf": {"hash": "abc123", "status": "ACCEPTED"}
    }


# -------------------------------------------------------------------
# Batch preview state
# -------------------------------------------------------------------

def test_load_processing_state_returns_hash_mapping(project):
    records = {
        "drawing.pdf": {"hash": "abc123", "status": "ACCEPTED"},
        "another.pdf": {"hash": "def456", "status": None},
    }

    processing_state.save_processing_state(project, records)

    assert processing_state.load_processing_state(project) == {
        "drawing.pdf": "abc123",
        "another.pdf": "def456",
    }


# -------------------------------------------------------------------
# Atomic state-file replacement
# -------------------------------------------------------------------

def test_save_processing_state_replaces_file_atomically(
    project, monkeypatch
):
    records = {
        "drawing.pdf": {"hash": "abc123", "status": "ACCEPTED"}
    }

    original_replace = Path.replace
    replace_calls = []

    def tracked_replace(path, target):
        replace_calls.append((path, target))
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", tracked_replace)

    processing_state.save_processing_state(project, records)

    state_file = processing_state.processing_state_path(project)
    temporary_file = state_file.with_suffix(".json.tmp")

    assert len(replace_calls) == 1
    assert replace_calls[0][1] == state_file
    assert state_file.is_file()
    assert not temporary_file.exists()
    assert processing_state.load_processing_records(project) == records


# -------------------------------------------------------------------
# Recent rejection activity
# -------------------------------------------------------------------

def test_missing_activity_log_returns_empty_rejections(isolated_paths):
    assert processing_state.load_recent_rejections(30) == {}


def test_recent_rejections_include_only_recent_rejected_pdfs(
    isolated_paths,
):
    admin_root, _ = isolated_paths
    activity_dir = admin_root / "activity"
    activity_dir.mkdir(parents=True)

    now = datetime.now().astimezone()

    entries = [
        {
            "status": "REJECTED",
            "project": "COOK",
            "pdf": "recent.pdf",
            "processed_at": now.isoformat(),
        },
        {
            "status": "REJECTED",
            "project": "COOK",
            "pdf": "old.pdf",
            "processed_at": (now - timedelta(days=10)).isoformat(),
        },
        {
            "status": "ACCEPTED",
            "project": "COOK",
            "pdf": "accepted.pdf",
            "processed_at": now.isoformat(),
        },
    ]

    activity_file = activity_dir / "BATCH_ACTIVITY.json"
    activity_file.write_text(
        json.dumps({"entries": entries}),
        encoding="utf-8",
    )

    assert processing_state.load_recent_rejections(2) == {
        "COOK": {"recent.pdf"}
    }


def test_malformed_activity_entries_are_ignored(isolated_paths):
    admin_root, _ = isolated_paths
    activity_dir = admin_root / "activity"
    activity_dir.mkdir(parents=True)

    entries = [
        None,
        "invalid entry",
        {"status": "REJECTED"},
        {
            "status": "REJECTED",
            "project": "COOK",
            "pdf": "bad-date.pdf",
            "processed_at": "not-a-date",
        },
    ]

    activity_file = activity_dir / "BATCH_ACTIVITY.json"
    activity_file.write_text(
        json.dumps({"entries": entries}),
        encoding="utf-8",
    )

    assert processing_state.load_recent_rejections(30) == {}


def test_naive_activity_timestamp_is_accepted(isolated_paths):
    admin_root, _ = isolated_paths
    activity_dir = admin_root / "activity"
    activity_dir.mkdir(parents=True)

    timestamp = datetime.now().isoformat()

    entries = [
        {
            "status": "REJECTED",
            "project": "COOK",
            "pdf": "legacy.pdf",
            "processed_at": timestamp,
        }
    ]

    activity_file = activity_dir / "BATCH_ACTIVITY.json"
    activity_file.write_text(
        json.dumps({"entries": entries}),
        encoding="utf-8",
    )

    assert processing_state.load_recent_rejections(30) == {
        "COOK": {"legacy.pdf"}
    }

