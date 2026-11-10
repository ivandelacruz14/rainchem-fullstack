    """Sends email. Mailjet is the default. Resend is an alternative (EMAIL_PROVIDER=resend), and it is also tried when
    the Mailjet connection keeps failing. Sensitive emails (codes, reset links) are never stored in full in notifications."""
    import os
    import time

    import requests
    from flask import current_app

    from app.extensions import db
    from app.models import Notification

    RETRY_DELAYS = (1, 2)
    MAILJET_URL = "https://api.mailjet.com/v3.1/send"
    RESEND_URL = "https://api.resend.com/emails"
    TIMEOUT_SECONDS = 15


    def _post_with_retry(url, **kwargs):
        """A dropped connection is retried twice. A reply from the provider, even an error, is final."""
        last = None
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                return requests.post(url, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as error:
                last = error
                if attempt < len(RETRY_DELAYS):
                    time.sleep(RETRY_DELAYS[attempt])
        raise last


    def _via_mailjet(to_email, subject, body, sender):
        api_key = os.environ.get("MAILJET_API_KEY", "")
        api_secret = os.environ.get("MAILJET_API_SECRET", "")
        if not api_key or not api_secret:
            return False, "MAILJET_API_KEY or MAILJET_API_SECRET is missing"
        try:
            response = _post_with_retry(
                MAILJET_URL,
                auth=(api_key, api_secret),
                json={"Messages": [{
                    "From": {"Email": sender, "Name": "Rainchem"},
                    "To": [{"Email": to_email}],
                    "Subject": subject,
                    "TextPart": body,
                }]},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            return False, f"Mailjet request error: {error}"
        if response.status_code >= 400:
            return False, f"Mailjet replied {response.status_code}: {response.text}"
        return True, None


    def _via_resend(to_email, subject, body, sender):
        api_key = os.environ.get("RESEND_API_KEY", "")
        if not api_key:
            return False, "RESEND_API_KEY is missing"
        try:
            response = _post_with_retry(
                RESEND_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"from": f"Rainchem <{sender}>", "to": [to_email], "subject": subject, "text": body},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            return False, f"Resend request error: {error}"
        if response.status_code >= 400:
            return False, f"Resend replied {response.status_code}: {response.text}"
        return True, None


    def send_email(to_email, subject, body, user_id=None, sensitive=False):
        sender = current_app.config.get("SMTP_FROM", "")
        provider = (current_app.config.get("EMAIL_PROVIDER") or "mailjet").lower()

        if not sender:
            sent, detail = False, "SMTP_FROM is missing"
        elif provider == "resend":
            sent, detail = _via_resend(to_email, subject, body, sender)
        else:
            sent, detail = _via_mailjet(to_email, subject, body, sender)
            connection_failed = not sent and "request error" in (detail or "")
            if connection_failed and os.environ.get("RESEND_API_KEY"):
                sent, detail = _via_resend(to_email, subject, body, sender)

        if not sent:
            print(f"\n--- EMAIL NOT SENT to {to_email} ---\nREASON: {detail}\n---\n", flush=True)
            # Only when running `python run.py` locally (Flask debug mode): show the message so a code can be copied.
            if current_app.debug:
                print(f"SUBJECT: {subject}\n{body}\n", flush=True)

        stored_body = "[content not stored: contains a private link or code]" if sensitive else body
        db.session.add(Notification(user_id=user_id, channel="email", subject=subject, body=stored_body))
        db.session.commit()
        return sent
