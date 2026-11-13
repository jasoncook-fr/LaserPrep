"""
batch_processing.py

Batch discovery, change scanning, and batch orchestration for LaserPrep.
"""

from pathlib import Path
from typing import Callable
import shutil

from batch_alerts import BatchAlerts
from config import (
    ADMIN_ROOT,
    REPORT_RETENTION_DAYS,
    STUDENT_DOCUMENTS_FOLDER,
    STUDENT_GUIDE,
    STUDENT_FILE_RETENTION_DAYS,
    STUDENT_CLEANUP_DRY_RUN,
)
from nextcloud_lookup import (
    get_student_emails,
    remove_share_expirations,
)
from notification_manager import NotificationManager
from processing_state import (
    load_processing_state,
    load_recent_rejections,
    pdf_hash,
)

from student_cleanup import cleanup_student_folders

IGNORED_PROJECT_FOLDERS = {
    STUDENT_DOCUMENTS_FOLDER.casefold(),
    "reports",
}


def prepare_student_documents(
    batch_root: Path,
    print_info: Callable[[str], None],
    print_warning: Callable[[str], None],
) -> None:
    """Create student Documents folders and distribute the user guide."""
    if not STUDENT_GUIDE.is_file():
        print_warning(f"Student guide not found: {STUDENT_GUIDE}")

    for student_folder in sorted(batch_root.iterdir()):
        if not student_folder.is_dir():
            continue

        documents_folder = student_folder / STUDENT_DOCUMENTS_FOLDER

        try:
            documents_folder.mkdir(exist_ok=True)

            if not STUDENT_GUIDE.is_file():
                continue

            destination = documents_folder / STUDENT_GUIDE.name

            if not destination.exists():
                shutil.copy2(STUDENT_GUIDE, destination)
                print_info(f"Distributed user guide: {student_folder.name}")

        except OSError as exc:
            print_warning(
                f"Could not prepare Documents for "
                f"{student_folder.name}: {exc}"
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
            if (
                project_folder.is_dir()
                and project_folder.name.casefold()
                not in IGNORED_PROJECT_FOLDERS
                and any(project_folder.glob("*.pdf"))
            ):
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
    """Process changed projects and retry pending notifications for unchanged ones."""
    if not batch_root.exists():
        print_error(f"Batch root does not exist: {batch_root}")
        return

    # Automatically remove expiration dates from student folder shares.
    try:
        share_summary = remove_share_expirations(dry_run=False)

        print_info(
            "Nextcloud share maintenance: "
            f"{share_summary['inspected']} shares inspected, "
            f"{share_summary['removed']} expiration dates removed."
        )

        if share_summary["failed"]:
            print_warning(
                f"Could not remove expiration dates from "
                f"{len(share_summary['failed'])} shares."
            )

            for failure in share_summary["failed"]:
                print_warning(
                    f"Share update failed: {failure['path']}: "
                    f"{failure['error']}"
                )

        elif share_summary["expiring"] == 0:
            print_info(
                "All folder shares are already without expiration dates."
            )

    except Exception as exc:
        print_warning(
            f"Nextcloud share maintenance failed: {exc}. "
            "Continuing with batch processing."
        )

    # Clean expired contents from student folders.
    # This runs even when there are no projects to process.
    try:
        cleanup_summary = cleanup_student_folders(
            batch_root,
            retention_days=STUDENT_FILE_RETENTION_DAYS,
            dry_run=STUDENT_CLEANUP_DRY_RUN,
        )

        if STUDENT_CLEANUP_DRY_RUN:
            file_count = len(cleanup_summary["expired_files"])
            directory_count = len(
                cleanup_summary["directories_to_remove"]
            )
            action = "would be deleted"
            mode = "DRY RUN"
        else:
            file_count = len(cleanup_summary["deleted_files"])
            directory_count = len(
                cleanup_summary["removed_directories"]
            )
            action = "deleted"
            mode = "LIVE"

        print_info(
            f"Student folder cleanup ({mode}): "
            f"{cleanup_summary['students_inspected']} students inspected, "
            f"{cleanup_summary['files_inspected']} files inspected."
        )
        print_info(
            f"Student folder cleanup: {file_count} files and "
            f"{directory_count} directories {action}."
        )

        if cleanup_summary["errors"]:
            print_warning(
                f"Student folder cleanup encountered "
                f"{len(cleanup_summary['errors'])} errors."
            )
            for error in cleanup_summary["errors"]:
                print_warning(
                    f"Cleanup error: {error['path']}: {error['error']}"
                )

    except Exception as exc:
        print_warning(
            f"Student folder cleanup failed: {exc}. "
            "Continuing with batch processing."
        )

    prepare_student_documents(
        batch_root,
        print_info,
        print_warning,
    )

    projects = []
    for student_folder in sorted(batch_root.iterdir()):
        if not student_folder.is_dir():
            continue
        if any(student_folder.glob("*.pdf")):
            projects.append((student_folder, student_folder.name))
        for project_folder in sorted(student_folder.iterdir()):
            if (
                project_folder.is_dir()
                and project_folder.name.casefold()
                not in IGNORED_PROJECT_FOLDERS
                and any(project_folder.glob("*.pdf"))
            ):
                projects.append(
                    (project_folder, f"{student_folder.name} / {project_folder.name}")
                )

    if not projects:
        print("No projects found.")
        return

    # Use the same change scanner as the GUI so unchanged projects are not
    # sent through process_project() on every batch run.
    changes_by_project = {
        change["project"]: change
        for change in scan_batch_changes(batch_root)
    }
    print_info(
        f"Found {len(projects)} projects; "
        f"{len(changes_by_project)} require processing."
    )

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
    skipped_projects = len(projects) - len(changes_by_project)
    processed_projects = 0
    processing_index = 0

    for folder, batch_project_name in projects:
        student_folder_name = (
            folder.name if folder.parent == batch_root else folder.parent.name
        )

        result = "skipped"
        if batch_project_name in changes_by_project:
            processing_index += 1
            result = process_project(
                folder,
                alerts,
                use_state=True,
                batch_project_name=batch_project_name,
                progress_label=(
                    f"Project {processing_index} / {len(changes_by_project)}"
                ),
            )
            if result == "skipped":
                skipped_projects += 1
            else:
                processed_projects += 1

        # Unchanged projects are not reprocessed, but pending notifications
        # are still retried for them.
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
