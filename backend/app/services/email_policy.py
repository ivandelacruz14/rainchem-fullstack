"""Rejects temporary (disposable) email domains. The starter list is short on purpose: add more domains with the
EXTRA_DISPOSABLE_DOMAINS environment variable (comma separated), or replace this list with a maintained one.
Checking the domain never proves the mailbox is real; the emailed code does that."""
import os

STARTER_DISPOSABLE = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.net", "10minutemail.com", "tempmail.com",
    "temp-mail.org", "yopmail.com", "trashmail.com", "throwawaymail.com", "sharklasers.com",
    "getnada.com", "dispostable.com", "fakeinbox.com", "maildrop.cc", "mailnesia.com",
}


def disposable_domains():
    extra = {d.strip().lower() for d in os.environ.get("EXTRA_DISPOSABLE_DOMAINS", "").split(",") if d.strip()}
    return STARTER_DISPOSABLE | extra


def is_disposable_email(email):
    domain = (email or "").rsplit("@", 1)[-1].strip().lower()
    return domain in disposable_domains()
