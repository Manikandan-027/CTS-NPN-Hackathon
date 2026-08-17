import os
from dotenv import load_dotenv

from src.email_service import fetch_unread_incident_emails


load_dotenv()


def main():
    incidents = fetch_unread_incident_emails(
        mailbox_email=os.environ["manikandan270706@gmail.com"],
        mailbox_app_password=os.environ["oeic etyj qvox ygyy"],
        sender_email=os.environ.get("GMAIL_SENDER"),
    )

    if not incidents:
        print("No unread RCA incident emails found.")
        return

    for incident in incidents:
        print("\n--- INCIDENT RECEIVED ---")
        print("Incident ID:", incident["incident_id"])
        print("Subject:", incident["subject"])
        print("From:", incident["from"])
        print(incident["body"])


if __name__ == "__main__":
    main()
