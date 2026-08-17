import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


load_dotenv()


def send_incident_email(incident: dict) -> bool:

    sender = os.getenv("GMAIL_SENDER")
    app_password = os.getenv("GMAIL_SENDER_APP_PASSWORD")
    developer_email = os.getenv("DEVELOPER_EMAIL")

    if not sender:
        raise RuntimeError("GMAIL_SENDER is not configured")

    if not app_password:
        raise RuntimeError(
            "GMAIL_SENDER_APP_PASSWORD is not configured"
        )

    if not developer_email:
        raise RuntimeError(
            "DEVELOPER_EMAIL is not configured"
        )

    subject = (
        f"[DEMO INCIDENT] "
        f"{incident['service']} - "
        f"{incident['error_code']} - "
        f"{incident['incident_id']}"
    )

    body = f"""New payment incident detected.

Incident ID:
{incident['incident_id']}

Service:
{incident['service']}

Environment:
{incident['environment']}

Error Code:
{incident['error_code']}

Error Message:
{incident['error_message']}

Timestamp:
{incident['timestamp']}

Request ID:
{incident['request_id']}

Source:
{incident['source']}

Status:
{incident['status']}

This email contains only the observed incident.

The RCA system must determine:
- Root cause
- Historical evidence
- Resolution
- Affected code
- Recommended fix
"""

    message = EmailMessage()

    message["From"] = sender
    message["To"] = developer_email
    message["Subject"] = subject

    message.set_content(body)

    print()
    print("[EMAIL] Sender:", sender)
    print("[EMAIL] Recipient:", developer_email)
    print("[EMAIL] Subject:", subject)
    print("[EMAIL] Connecting to Gmail SMTP...")

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=30,
    ) as smtp:

        smtp.login(
            sender,
            app_password,
        )

        print("[EMAIL] Gmail login successful")

        smtp.send_message(message)

    print(
        f"[EMAIL SENT] {incident['incident_id']}"
    )

    return True