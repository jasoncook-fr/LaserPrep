"""
processing_state.py

LaserPrep processing-state and cache management.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from config import ADMIN_ROOT, BATCH_ROOT


def pdf_hash(path: Path) -> str:
    """Return a SHA-256 hash of a PDF's contents."""

    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()

def processing_state_path(folder: Path) -> Path:
    """Return the administrator-only state file for a project."""

    state_dir = ADMIN_ROOT / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    if folder.parent == BATCH_ROOT:
        filename = f"{folder.name}.json"
    else:
        filename = f"{folder.parent.name}__{folder.name}.json"

    return state_dir / filename


def load_processing_records(folder: Path) -> dict[str, dict]:
    """Load per-PDF hashes and cached report outcomes.

    Legacy state files (a simple filename-to-hash mapping) are accepted.
    They have no cached report outcomes, so those PDFs are reprocessed once
    to establish the richer state format.
    """
    state_file = processing_state_path(folder)

    if not state_file.exists():
        return {}

    try:
        with state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    if isinstance(data, dict) and isinstance(data.get("files"), dict):
        return {
            name: record
            for name, record in data["files"].items()
            if isinstance(record, dict) and isinstance(record.get("hash"), str)
        }

    # Backward compatibility: old format stored only successful PDF hashes.
    if isinstance(data, dict):
        return {
            name: {"hash": value, "status": None}
            for name, value in data.items()
            if isinstance(name, str) and isinstance(value, str)
        }

    return {}


def load_processing_state(folder: Path) -> dict[str, str]:
    """Return filename-to-hash state for the batch preview."""
    return {
        name: record["hash"]
        for name, record in load_processing_records(folder).items()
    }


def save_processing_state(folder: Path, records: dict[str, dict]) -> None:
    """Atomically save content hashes and per-PDF report outcomes."""
    state_file = processing_state_path(folder)
    tmp_path = state_file.with_suffix(state_file.suffix + ".tmp")

    payload = {"version": 2, "files": records}
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    tmp_path.replace(state_file)

def load_recent_rejections(retention_days: int) -> dict[str, set[str]]:
    """Return rejected PDFs processed within the rolling activity window.

    The admin activity log is the source of truth. Old rejection entries are
    ignored even if the student-facing base report still contains them.
    """
    activity_path = ADMIN_ROOT / "activity" / "BATCH_ACTIVITY.json"

    if not activity_path.is_file():
        return {}

    try:
        with activity_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    entries = data.get("entries", []) if isinstance(data, dict) else []
    if not isinstance(entries, list):
        return {}

    cutoff = datetime.now().astimezone() - timedelta(
        days=max(1, int(retention_days))
    )
    recent_rejections: dict[str, set[str]] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "REJECTED":
            continue

        project = entry.get("project")
        pdf = entry.get("pdf")
        processed_at = entry.get("processed_at")
        if not all(isinstance(value, str) and value for value in (project, pdf, processed_at)):
            continue

        try:
            timestamp = datetime.fromisoformat(processed_at)
        except ValueError:
            continue

        # Older activity-log entries should normally include a timezone.
        # Treat a legacy naive timestamp as local time rather than discarding it.
        if timestamp.tzinfo is None:
            timestamp = timestamp.astimezone()

        if timestamp >= cutoff:
            recent_rejections.setdefault(project, set()).add(pdf)

    return recent_rejections
