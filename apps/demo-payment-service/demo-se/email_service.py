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
        raise RuntimeError(
            "GMAIL_SENDER is not configured"
        )

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
        f"{incident['error_code']}"
    )

    body = f"""
New payment incident detected.

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

This email contains the observed incident only.
Root cause and resolution must be determined by the RCA system.
"""

    message = EmailMessage()

    message["From"] = sender
    message["To"] = developer_email
    message["Subject"] = subject

    message.set_content(body)

    print("[EMAIL] Connecting to Gmail SMTP...")

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465
    ) as smtp:

        smtp.login(
            sender,
            app_password
        )

        smtp.send_message(message)

    print(
        f"[EMAIL SENT] Incident {incident['incident_id']}"
    )

    return True