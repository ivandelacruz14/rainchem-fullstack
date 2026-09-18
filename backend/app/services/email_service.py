"""
Sends outgoing notifications (verification codes, password resets, order
updates). If SMTP settings are configured in the environment, a real email
is sent. Otherwise the message is printed to the console and saved to the
notifications table, so nothing is silently lost during development.
"""

import smtplib
from email.mime.text import MIMEText
from flask import current_app
from app.extensions import db
from app.models import Notification


def send_email(to_email, subject, body, user_id=None):
    config = current_app.config
    sent_via_smtp = False

    if config.get("SMTP_HOST"):
        try:
            message = MIMEText(body)
            message["Subject"] = subject
            message["From"] = config["SMTP_FROM"]
            message["To"] = to_email

            with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"]) as server:
                server.starttls()
                if config.get("SMTP_USERNAME"):
                    server.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
                server.sendmail(config["SMTP_FROM"], [to_email], message.as_string())
            sent_via_smtp = True
        except Exception as error:
            current_app.logger.warning("Failed to send email via SMTP: %s", error)

    if not sent_via_smtp:
        print(f"\n--- Email to {to_email} ---\nSubject: {subject}\n\n{body}\n---\n")

    notification = Notification(user_id=user_id, channel="email", subject=subject, body=body)
    db.session.add(notification)
    db.session.commit()

    return sent_via_smtp
