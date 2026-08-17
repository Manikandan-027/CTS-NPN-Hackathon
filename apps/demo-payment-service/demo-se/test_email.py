import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

sender = os.getenv("GMAIL_SENDER")
password = os.getenv("GMAIL_SENDER_APP_PASSWORD")
recipient = os.getenv("DEVELOPER_EMAIL")

print("Sender:", sender)
print("Recipient:", recipient)
print("Password configured:", bool(password))

message = EmailMessage()

message["From"] = sender
message["To"] = recipient
message["Subject"] = "RCA Demo - Gmail Test"

message.set_content(
    """Hello,

This is a test email from the AI RCA Demo Payment Service.

If you received this email, Gmail SMTP delivery is working correctly.

Regards,
AI RCA Demo
"""
)

print("Connecting to Gmail...")

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:

    print("Logging into Gmail...")

    smtp.login(sender, password)

    print("Sending email...")

    smtp.send_message(message)

print("EMAIL SENT SUCCESSFULLY")