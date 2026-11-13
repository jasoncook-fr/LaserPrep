
"""
student_cleanup.py

LaserPrep student folder cleanup.

Deletes files and empty directories older than the retention period
from student folders.

Protection rules:
- Every directory named "Documents" is completely preserved,
  including all its contents, at any nesting level.
- Student root directories are never removed.
- Symbolic links are never followed.

Each filesystem entry is evaluated independently using its own
modification time (mtime).
"""

import os
import stat
import time
from pathlib import Path


def cleanup_student_folders(
    batch_root: Path,
    retention_days: int = 30,
    dry_run: bool = True,
) -> dict:
    """
    Remove expired contents from student folders.

    Rules:
    - Non-directory entries older than retention_days are deleted.
    - Directories are removed only when:
        1. Their own modification time is older than the cutoff.
        2. They are empty after processing their contents.
    - Recent files and directories are preserved.
    - Every directory named "Documents" is completely preserved.
    - Student root directories are never removed.
    - Symbolic links are never followed.

    Args:
        batch_root: Root directory containing student folders.
        retention_days: Age threshold in days.
        dry_run: Report deletion candidates without deleting them.

    Returns:
        A summary containing inspected entries, deletion candidates,
        completed deletions, and errors.
    """

    batch_root = Path(batch_root)

    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")

    if not batch_root.is_dir():
        raise FileNotFoundError(
            f"Student batch directory not found: {batch_root}"
        )

    cutoff = time.time() - (retention_days * 86400)

    summary = {
        "students_inspected": 0,
        "files_inspected": 0,
        "expired_files": [],
        "deleted_files": [],
        "directories_to_remove": [],
        "removed_directories": [],
        "errors": [],
        "dry_run": dry_run,
    }

    def record_error(path: Path, exc: Exception) -> None:
        summary["errors"].append({
            "path": str(path),
            "error": str(exc),
        })

    def clean_directory(directory: Path) -> bool:
        """
        Process a directory's contents recursively.

        Returns True if the directory will be empty after cleanup.

        The caller independently evaluates the directory's own
        modification time before deciding whether to remove it.
        """

        will_be_empty = True

        try:
            with os.scandir(directory) as iterator:
                entries = sorted(
                    iterator,
                    key=lambda entry: entry.name,
                )
        except OSError as exc:
            record_error(directory, exc)
            return False

        for entry in entries:
            path = Path(entry.path)

            try:
                # lstat-style information: never follow symlinks.
                info = entry.stat(follow_symlinks=False)

                if stat.S_ISDIR(info.st_mode):
                    # Preserve Documents directories and all contents.
                    if entry.name.casefold() == "documents":
                        will_be_empty = False
                        continue

                    child_will_be_empty = clean_directory(path)

                    # A directory must independently be expired
                    # and empty before it can be removed.
                    if (
                        child_will_be_empty
                        and info.st_mtime < cutoff
                    ):
                        summary["directories_to_remove"].append(
                            str(path)
                        )

                        if not dry_run:
                            try:
                                path.rmdir()
                                summary["removed_directories"].append(
                                    str(path)
                                )
                            except OSError as exc:
                                record_error(path, exc)
                                will_be_empty = False
                    else:
                        will_be_empty = False

                else:
                    # All non-directory entries are evaluated,
                    # including hidden files, symlinks and special
                    # filesystem entries. Unlink never follows links.
                    summary["files_inspected"] += 1

                    if info.st_mtime < cutoff:
                        summary["expired_files"].append(str(path))

                        if not dry_run:
                            try:
                                path.unlink()
                                summary["deleted_files"].append(
                                    str(path)
                                )
                            except OSError as exc:
                                record_error(path, exc)
                                will_be_empty = False
                    else:
                        will_be_empty = False

            except OSError as exc:
                record_error(path, exc)
                will_be_empty = False

        return will_be_empty

    try:
        students = sorted(
            batch_root.iterdir(),
            key=lambda path: path.name,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Could not inspect student directory: {exc}"
        ) from exc

    for student_folder in students:
        try:
            info = student_folder.lstat()

            # Only inspect real student directories.
            # Never follow symbolic links at the student root.
            if not stat.S_ISDIR(info.st_mode):
                continue

            summary["students_inspected"] += 1
            clean_directory(student_folder)

        except OSError as exc:
            record_error(student_folder, exc)

    return summary
