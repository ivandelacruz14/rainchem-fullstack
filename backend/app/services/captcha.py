"""Cloudflare Turnstile ("I'm not a robot") check for sign-in, registration, and password reset.

The browser gets a one-time token from Turnstile. The server sends that token to Cloudflare with the secret key
and only continues when Cloudflare says it is valid. With no secret key configured (local development), nothing is
checked. When Cloudflare cannot be reached, the request is refused rather than allowed."""
import requests
from flask import current_app, request

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TIMEOUT_SECONDS = 8


class CaptchaError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def enabled():
    return bool(current_app.config.get("TURNSTILE_SECRET_KEY"))


def verify(token):
    if not enabled():
        return
    token = str(token or "").strip()
    if not token or len(token) > 2048:
        raise CaptchaError("Please complete the security check.")
    try:
        response = requests.post(
            VERIFY_URL,
            data={
                "secret": current_app.config["TURNSTILE_SECRET_KEY"],
                "response": token,
                "remoteip": request.remote_addr or "",
            },
            timeout=TIMEOUT_SECONDS,
        )
        body = response.json()
    except (requests.RequestException, ValueError):
        raise CaptchaError("The security check is unavailable right now. Please try again.", 503)
    if not response.ok or not isinstance(body, dict) or body.get("success") is not True:
        raise CaptchaError("The security check failed. Please try again.")
