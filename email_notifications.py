
#!/usr/bin/env python3

"""Send LaserPrep email notifications using the school's SMTP server."""

import argparse
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP_SSL


CONFIG_FILE = Path.home() / ".config" / "laserprep" / "email.env"


def load_email_config():
    """Load SMTP settings from the local email.env file."""

    if not CONFIG_FILE.is_file():
        raise FileNotFoundError(
            f"Email configuration not found: {CONFIG_FILE}"
        )

    config = {}

    for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")

    required = (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM",
    )

    missing = [key for key in required if not config.get(key)]

    if missing:
        raise ValueError(
            "Missing email configuration values: " + ", ".join(missing)
        )

    config["SMTP_PORT"] = int(config["SMTP_PORT"])

    return config


def send_email(recipient, subject, body):
    """Send a plain-text email."""

    config = load_email_config()

    message = EmailMessage()
    message["From"] = config["SMTP_FROM"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()

    with SMTP_SSL(
        config["SMTP_HOST"],
        config["SMTP_PORT"],
        context=context,
        timeout=20,
    ) as smtp:
        smtp.login(
            config["SMTP_USERNAME"],
            config["SMTP_PASSWORD"],
        )
        smtp.send_message(message)

    print(f"Email successfully sent to {recipient}")


def send_project_notification(recipient: str, project_name: str) -> None:
    """Notify a student that their LaserPrep project has been processed."""

    send_email(
        recipient=recipient,
        subject=f"[LaserPrep] Votre projet a été traité : {project_name}",
        body=(
            "Bonjour,\n\n"
            f"Le traitement de votre projet « {project_name} » est terminé.\n\n"
            "Vous pouvez consulter le rapport de traitement ainsi que "
            "le fichier SVG généré dans votre dossier partagé sur "
            "l'espace de stockage de l'école (Nextcloud).\n\n"
            "Merci de vérifier les résultats, notamment les éventuels "
            "avertissements et éléments rejetés.\n\n"
            "Besoin d'aide pour préparer votre fichier ?\n\n"
            "Si vous rencontrez des difficultés lors de la préparation "
            "de votre fichier, vous pouvez consulter le guide :\n"
            "https://www.montpellier.archi.fr/wp-content/uploads/"
            "Guide-Moniteur-Version-numerique.pdf\n\n"
            "Cordialement,\n\n"
            "Atelier Maquette"
        ),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Test LaserPrep email notifications."
    )
    parser.add_argument(
        "recipient",
        help="Email address to receive the test message.",
    )
    args = parser.parse_args()

    try:
        send_email(
            recipient=args.recipient,
            subject="[LaserPrep] Test d'envoi",
            body=(
                "Bonjour,\n\n"
                "Ceci est un message de test envoyé par LaserPrep.\n\n"
                "Si vous recevez ce message, la configuration SMTP "
                "fonctionne correctement.\n\n"
                "Cordialement,\n"
                "Atelier Maquette"
            ),
        )
    except Exception as error:
        print(f"Email sending failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
