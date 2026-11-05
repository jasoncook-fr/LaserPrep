
#!/usr/bin/env python3

"""Retrieve student email addresses from Nextcloud folder shares."""

import base64
import json
import os
import ssl
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CONFIG_FILE = Path.home() / ".config" / "laserprep" / "email.env"

CERTIFICATE_FILE = (
    Path.home()
    / ".config"
    / "laserprep"
    / "certs"
    / "HARICA-GEANT-TLS-E1.pem"
)

SHARES_ENDPOINT = (
    "/ocs/v2.php/apps/files_sharing/api/v1/shares"
)

STUDENT_ROOT = "/LaserPrep/STUDENTS"


def load_config() -> dict[str, str]:
    """Load Nextcloud credentials from the local configuration file."""

    if not CONFIG_FILE.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_FILE}"
        )

    config = {}

    for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")

    required = (
        "NEXTCLOUD_URL",
        "NEXTCLOUD_USERNAME",
        "NEXTCLOUD_APP_PASSWORD",
    )

    missing = [key for key in required if not config.get(key)]

    if missing:
        raise ValueError(
            "Missing configuration values: " + ", ".join(missing)
        )

    return config


def get_student_emails() -> dict[str, str]:
    """
    Retrieve internal student shares and return:
        {student_folder_name: student_email}
    """

    config = load_config()

    base_url = config["NEXTCLOUD_URL"].rstrip("/")
    username = config["NEXTCLOUD_USERNAME"]
    password = config["NEXTCLOUD_APP_PASSWORD"]

    params = urlencode({
        "path": STUDENT_ROOT,
        "subfiles": "true",
        "format": "json",
    })

    url = f"{base_url}{SHARES_ENDPOINT}?{params}"

    credentials = base64.b64encode(
        f"{username}:{password}".encode("utf-8")
    ).decode("ascii")

    request = Request(
        url,
        headers={
            "Authorization": f"Basic {credentials}",
            "OCS-APIRequest": "true",
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context()

    if CERTIFICATE_FILE.is_file():
        context.load_verify_locations(cafile=str(CERTIFICATE_FILE))

    try:
        with urlopen(request, context=context, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))

    except HTTPError as error:
        raise RuntimeError(
            f"Nextcloud returned HTTP {error.code}."
        ) from None

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to Nextcloud: {error.reason}"
        ) from None

    except json.JSONDecodeError:
        raise RuntimeError(
            "Nextcloud returned an invalid JSON response."
        ) from None

    ocs = result.get("ocs", {})
    meta = ocs.get("meta", {})

    if meta.get("status") != "ok":
        raise RuntimeError(
            f"Nextcloud API error: {meta.get('message', 'Unknown error')}"
        )

    shares = ocs.get("data", [])

    # Collect distinct email addresses for each student folder.
    candidates: dict[str, set[str]] = {}

    for share in shares:
        # Only consider internal Nextcloud user shares.
        if share.get("share_type") != 0:
            continue

        path = share.get("path", "")
        email = (
            share.get("share_with_displayname_unique") or ""
        ).strip()

        if not email or "@" not in email:
            continue

        # Only accept direct children of STUDENT_ROOT.
        if not path.startswith(STUDENT_ROOT + "/"):
            continue

        folder_name = path[len(STUDENT_ROOT) + 1:]

        if not folder_name or "/" in folder_name:
            continue

        candidates.setdefault(folder_name, set()).add(email)

    # Only return unambiguous folder-to-email mappings.
    student_emails = {}

    for folder, emails in candidates.items():
        if len(emails) == 1:
            student_emails[folder] = next(iter(emails))
        else:
            print(
                f"WARNING: Multiple recipient addresses for {folder}; "
                "skipping this folder."
            )

    return student_emails


if __name__ == "__main__":
    try:
        emails = get_student_emails()

        print(f"\nFound {len(emails)} student email mappings:\n")

        for folder, email in sorted(emails.items()):
            print(f"{folder} -> {email}")

    except Exception as error:
        print(f"\nNextcloud lookup failed: {error}")
        raise SystemExit(1)
