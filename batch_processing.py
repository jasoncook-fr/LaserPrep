"""
batch_processing.py

Batch discovery, change scanning, and batch orchestration for LaserPrep.
"""

from pathlib import Path
from typing import Callable

from batch_alerts import BatchAlerts
from config import ADMIN_ROOT, REPORT_RETENTION_DAYS
from nextcloud_lookup import get_student_emails
from notification_manager import NotificationManager
from processing_state import (
    load_processing_state,
    load_recent_rejections,
    pdf_hash,
)


def scan_batch_changes(batch_root: Path) -> list[dict]:
    """Return projects containing new, changed, rejected, or removed PDFs."""
    changes = []
    if not batch_root.is_dir():
        return changes

    projects = []
    for student_folder in sorted(batch_root.iterdir()):
        if not student_folder.is_dir():
            continue
        if any(student_folder.glob("*.pdf")):
            projects.append((student_folder, student_folder.name))
        for project_folder in sorted(student_folder.iterdir()):
            if project_folder.is_dir() and any(project_folder.glob("*.pdf")):
                projects.append(
                    (project_folder, f"{student_folder.name} / {project_folder.name}")
                )

    recent_rejections = load_recent_rejections(REPORT_RETENTION_DAYS)

    for folder, batch_project_name in projects:
        pdf_files = sorted(folder.glob("*.pdf"))
        current_hashes = {pdf.name: pdf_hash(pdf) for pdf in pdf_files}
        previous_hashes = load_processing_state(folder)
        rejected_names = recent_rejections.get(batch_project_name, set())

        new_files = sorted(
            name for name in current_hashes
            if name not in previous_hashes and name not in rejected_names
        )
        rejected_files = sorted(
            name for name in current_hashes
            if name in rejected_names
            and (
                name not in previous_hashes
                or current_hashes[name] == previous_hashes[name]
            )
        )
        changed_files = sorted(
            name for name in current_hashes
            if name in previous_hashes
            and current_hashes[name] != previous_hashes[name]
        )
        removed_files = sorted(
            name for name in previous_hashes if name not in current_hashes
        )

        if new_files or changed_files or removed_files:
            changes.append({
                "project": batch_project_name,
                "kind": (
                    "new"
                    if not previous_hashes and new_files
                    and not rejected_files and not changed_files and not removed_files
                    else "updated"
                ),
                "new": new_files,
                "rejected": rejected_files,
                "changed": changed_files,
                "removed": removed_files,
            })
        elif rejected_files:
            changes.append({
                "project": batch_project_name,
                "kind": "updated",
                "new": [],
                "rejected": rejected_files,
                "changed": [],
                "removed": [],
            })
    return changes


def process_batch(
    batch_root: Path,
    process_project: Callable[..., str],
    print_error: Callable[[str], None],
    print_info: Callable[[str], None],
    print_warning: Callable[[str], None],
    send_notifications: bool = True,
) -> None:
    """Process every project found under the selected batch root."""
    if not batch_root.exists():
        print_error(f"Batch root does not exist: {batch_root}")
        return

    projects = []
    for student_folder in sorted(batch_root.iterdir()):
        if not student_folder.is_dir():
            continue
        if any(student_folder.glob("*.pdf")):
            projects.append((student_folder, student_folder.name))
        for project_folder in sorted(student_folder.iterdir()):
            if project_folder.is_dir() and any(project_folder.glob("*.pdf")):
                projects.append(
                    (project_folder, f"{student_folder.name} / {project_folder.name}")
                )

    if not projects:
        print("No projects found.")
        return

    print_info(f"Found {len(projects)} projects.")
    notifications = None
    notification_status = "disabled"

    if send_notifications:
        try:
            student_emails = get_student_emails()
            print_info(
                f"Retrieved {len(student_emails)} student email mappings "
                "from Nextcloud."
            )
        except Exception as exc:
            student_emails = {}
            print_warning(
                f"Could not retrieve student shares from Nextcloud: {exc}. "
                "Email notifications will be deferred."
            )
        try:
            notifications = NotificationManager(
                ADMIN_ROOT, batch_root, student_emails
            )
            notification_status = "enabled"
        except Exception as exc:
            notification_status = "unavailable"
            print_warning(
                f"Could not initialize notification history: {exc}. "
                "Email notifications are disabled for this batch."
            )
    else:
        print_info("Email notifications are disabled for this batch.")

    alerts = BatchAlerts()
    skipped_projects = 0
    processed_projects = 0

    for i, (folder, batch_project_name) in enumerate(projects, start=1):
        result = process_project(
            folder,
            alerts,
            use_state=True,
            batch_project_name=batch_project_name,
            progress_label=f"Project {i} / {len(projects)}",
        )
        if result == "skipped":
            skipped_projects += 1
        else:
            processed_projects += 1

        student_folder_name = (
            folder.name if folder.parent == batch_root else folder.parent.name
        )

        if notifications is not None:
            try:
                if result == "completed":
                    notifications.queue(folder, batch_project_name)
                    notifications.attempt(folder, student_folder_name)
                elif result == "skipped":
                    notifications.attempt(folder, student_folder_name)
                else:
                    notifications.clear(folder)
            except Exception as exc:
                if hasattr(notifications, "record_pending"):
                    notifications.record_pending(
                        batch_project_name,
                        f"Notification handling failed: {exc}",
                    )
                print_warning(
                    f"Notification handling failed for {batch_project_name}: {exc}"
                )

    if notifications is not None:
        notification_summary = notifications.get_run_summary()
    else:
        notification_summary = {
            "status": notification_status,
            "sent": [],
            "pending": [],
        }

    alerts.save(
        ADMIN_ROOT,
        retention_days=REPORT_RETENTION_DAYS,
        notification_summary=notification_summary,
    )
    print_info("=" * 60)
    print_info("Batch summary")
    print_info("=" * 60)
    print_info(f"Projects found     : {len(projects)}")
    print_info(f"Projects processed : {processed_projects}")
    print_info(f"Projects skipped   : {skipped_projects}")
    print_info("=" * 60)
