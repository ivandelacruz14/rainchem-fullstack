import requests
from flask import current_app

from app.extensions import db
from app.models import Notification


def send_email(to_email, subject, body, user_id=None):
    config = current_app.config

    api_key = config.get("RESEND_API_KEY", "")
    sender = config.get("SMTP_FROM", "onboarding@resend.dev")

    sent = False
    error_detail = None

    if not api_key:
        error_detail = "RESEND_API_KEY is empty or not loaded from config"

    else:
        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"Rainchem <{sender}>",
                    "to": [to_email],
                    "subject": subject,
                    "text": body,
                },
                timeout=15,
            )

            if response.status_code >= 400:
                error_detail = (
                    f"Resend replied {response.status_code}: "
                    f"{response.text}"
                )

            else:
                sent = True

                print(
                    "\n--- EMAIL SENT THROUGH RESEND ---\n"
                    f"To: {to_email}\n"
                    f"Status Code: {response.status_code}\n"
                    f"Response: {response.text}\n"
                    "---\n",
                    flush=True,
                )

        except requests.RequestException as error:
            error_detail = f"Request error: {error}"

    if not sent:
        print(
            "\n--- EMAIL NOT SENT ---\n"
            f"To: {to_email}\n"
            f"REASON: {error_detail}\n"
            f"Subject: {subject}\n"
            "---\n",
            flush=True,
        )

    # Save notification to database
    db.session.add(
        Notification(
            user_id=user_id,
            channel="email",
            subject=subject,
            body=body,
        )
    )

    db.session.commit()

    return sent