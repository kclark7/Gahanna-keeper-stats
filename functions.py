import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

def send_email(subject, body, html=False):
    # Create the email
    load_dotenv(override=True)
    sender_email = os.getenv("GMAIL_SENDER")
    sender_password = os.getenv("GMAIL_PASSWORD")

    print(f"Trying to send email from {sender_email}")
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = sender_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html" if html else "plain"))

    try:
        # Connect to Gmail’s SMTP server (use your provider’s server if different)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("clarkkyle11@gmail.com", sender_password)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")