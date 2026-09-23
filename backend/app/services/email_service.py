import os

import requests
from flask import current_app

from app.extensions import db
from app.models import Notification


def send_email(to_email, subject, body, user_id=None):
    api_key = os.environ.get("MAILJET_API_KEY", "")
    api_secret = os.environ.get("MAILJET_API_SECRET", "")
    sender_email = current_app.config.get("SMTP_FROM", "")

    sent = False
    error_detail = None

    if not api_key or not api_secret or not sender_email:
        error_detail = "MAILJET_API_KEY, MAILJET_API_SECRET, or SMTP_FROM is missing"
    else:
        try:
            response = requests.post(
                "https://api.mailjet.com/v3.1/send",
                auth=(api_key, api_secret),
                json={
                    "Messages": [{
                        "From": {"Email": sender_email, "Name": "Rainchem"},
                        "To": [{"Email": to_email}],
                        "Subject": subject,
                        "TextPart": body,
                    }]
                },
                timeout=15,
            )
            if response.status_code >= 400:
                error_detail = f"Mailjet replied {response.status_code}: {response.text}"
            else:
                sent = True
        except requests.RequestException as error:
            error_detail = f"Request error: {error}"

    if not sent:
        print(f"\n--- EMAIL NOT SENT to {to_email} ---\nREASON: {error_detail}\n---\n", flush=True)

    db.session.add(Notification(user_id=user_id, channel="email", subject=subject, body=body))
    db.session.commit()
    return sent