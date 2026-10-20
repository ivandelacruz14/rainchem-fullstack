"""
Verifies the ID token sent by Google Identity Services on the frontend.

The frontend loads Google's "Sign in with Google" button, which returns a
signed ID token after the user authenticates with their Google account.
That token is sent here and checked against Google's servers before we
trust the email address inside it.
"""

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import current_app


def verify_google_token(token):
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ValueError("Google sign-in is not configured on this server yet")

    # A few seconds of allowed clock difference: without it Google's token can be
    # refused as "used too early" when this server's clock is slightly behind.
    payload = id_token.verify_oauth2_token(
        token, google_requests.Request(), client_id, clock_skew_in_seconds=10
    )

    email = payload["email"].strip().lower()
    return {
        "google_id": payload["sub"],
        "email": email,
        "name": payload.get("name") or email.split("@")[0],
        "email_verified": payload.get("email_verified", False),
    }
