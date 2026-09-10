import os
from dotenv import load_dotenv

from src.payment.incident_catalog import (
    INCIDENTS,
    DEFAULT_INCIDENT_ID,
)
from src.payment.payment_service import (
    PaymentFailure,
    process_payment,
)
from src.email_service import send_incident_email


load_dotenv()


def main():
    incident_id = os.getenv(
        "DEMO_INCIDENT_ID",
        DEFAULT_INCIDENT_ID,
    )

    incident = INCIDENTS[incident_id]

    try:
        process_payment(
            customer="Demo Customer",
            card="4242 4242 4242 4242",
            amount=4999,
        )

    except PaymentFailure as exc:

        print("❌ Payment Failed")
        print(str(exc))

        send_incident_email(
            incident_id=incident_id,
            observed_error=str(exc),
            service=incident["affected_service"],
            environment=incident["environment"],
            sender_email=os.environ["GMAIL_SENDER"],
            sender_app_password=os.environ["GMAIL_SENDER_APP_PASSWORD"],
            developer_email=os.environ["DEVELOPER_EMAIL"],
        )

        print("📧 Incident email sent to developer.")

    else:
        print("Payment unexpectedly succeeded.")


if __name__ == "__main__":
    main()
