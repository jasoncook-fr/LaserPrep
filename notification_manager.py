#!/usr/bin/env python3

"""Queue, send, and retry LaserPrep student email notifications."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from email_notifications import send_project_notification


class NotificationManager:
    """Maintain notification state independently from processing state."""

    def __init__(
        self,
        admin_root: Path,
        batch_root: Path,
        student_emails: dict[str, str],
    ) -> None:
        self.batch_root = batch_root
        self.student_emails = student_emails
        self.state_dir = admin_root / "notifications"
        self.state_file = self.state_dir / "notification_state.json"
        self.records = self._load_state()
        self.run_results: list[dict] = []

    def _load_state(self) -> dict:
        if not self.state_file.is_file():
            return {}

        try:
            with self.state_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARNING: Could not read notification history: {exc}")
            return {}

        if not isinstance(data, dict):
            print("WARNING: Notification history has an invalid format.")
            return {}

        return data

    def _save_state(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temporary_file = self.state_file.with_suffix(".json.tmp")

        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(self.records, file, indent=2, sort_keys=True)

        temporary_file.replace(self.state_file)

    def _project_key(self, folder: Path) -> str:
        return folder.relative_to(self.batch_root).as_posix()

    @staticmethod
    def _project_signature(folder: Path) -> str:
        """Hash PDF names and contents to identify this project version."""
        digest = hashlib.sha256()

        for pdf in sorted(folder.glob("*.pdf")):
            digest.update(pdf.name.encode("utf-8"))
            digest.update(b"\0")

            with pdf.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)

            digest.update(b"\0")

        return digest.hexdigest()

    def queue(self, folder: Path, project_label: str) -> None:
        """Queue a notification after a completed processing run."""
        key = self._project_key(folder)
        signature = self._project_signature(folder)
        previous = self.records.get(key, {})

        # Never resend a notification for the same successfully notified
        # version, even if LaserPrep has to regenerate its SVG.
        if (
            isinstance(previous, dict)
            and previous.get("signature") == signature
            and previous.get("status") == "sent"
        ):
            return

        # Preserve an existing pending notification for this same version.
        if (
            isinstance(previous, dict)
            and previous.get("signature") == signature
            and previous.get("status") == "pending"
        ):
            return

        self.records[key] = {
            "signature": signature,
            "project_label": project_label,
            "status": "pending",
        }
        self._save_state()

    def clear(self, folder: Path) -> None:
        """Discard pending notifications when no PDF was available to process."""
        key = self._project_key(folder)

        if key in self.records:
            del self.records[key]
            self._save_state()

    def attempt(self, folder: Path, student_folder_name: str) -> None:
        """Send a matching pending notification, or leave it pending to retry."""
        key = self._project_key(folder)
        record = self.records.get(key)

        if not isinstance(record, dict) or record.get("status") != "pending":
            return

        current_signature = self._project_signature(folder)

        # Do not send a notification for an older version of the PDFs.
        if record.get("signature") != current_signature:
            del self.records[key]
            self._save_state()
            return

        recipient = self.student_emails.get(student_folder_name)
        if not recipient:
            self.record_pending(
                record.get("project_label", folder.name),
                "No student email address found",
            )
            print(
                f"WARNING: No Nextcloud student share/email found for "
                f"{student_folder_name}; notification remains pending."
            )
            return

        project_label = record.get("project_label", folder.name)

        try:
            send_project_notification(recipient, project_label)
        except Exception as exc:
            self.record_pending(
                project_label,
                f"Email delivery failed: {exc}",
            )
            print(
                f"WARNING: Could not send notification for "
                f"{project_label}: {exc}"
            )
            return

        self.run_results.append({
            "project": project_label,
            "status": "sent",
            "detail": "",
        })

        record["status"] = "sent"
        record["sent_at"] = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )

        try:
            self._save_state()
        except OSError as exc:
            print(
                f"WARNING: Email was sent to {recipient}, but notification "
                f"history could not be saved: {exc}. A duplicate may be sent "
                "on a later batch run."
            )
            return

        print(f"Notification recorded for {project_label}.")

    def record_pending(self, project_label: str, detail: str) -> None:
        """Record a notification that could not be completed in this run."""
        self.run_results.append({
            "project": project_label,
            "status": "pending",
            "detail": detail,
        })

    def get_run_summary(self) -> dict:
        """Return notification outcomes from the current batch run."""
        return {
            "status": "enabled",
            "sent": [
                result for result in self.run_results
                if result["status"] == "sent"
            ],
            "pending": [
                result for result in self.run_results
                if result["status"] == "pending"
            ],
        }
