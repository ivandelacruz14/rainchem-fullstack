"""Decides when the AI assistant should offer a person instead.

It uses what the retrieval already knows: how the answer was found (source), whether it was
resolved, and how many recent answers were incomplete. An unfamiliar question alone does not
trigger it when the assistant still has related answers to offer."""
import re

from app.models import ChatLog

NO_ANSWER_MESSAGE = (
    "I may not have enough information to answer your question accurately. "
    "Would you like to chat with our admin for further assistance?"
)
REPEATED_MESSAGE = (
    "I'm still not able to give you a complete answer. "
    "Would you like to chat with our admin so a person can help?"
)
REQUESTED_MESSAGE = "Sure, I can connect you with our admin. Would you like to open the live chat?"
LOW_RATING_MESSAGE = "Sorry that answer did not help. Would you like to chat with our admin for further assistance?"

_VERBS = r"(talk|speak|chat|connect|contact|message|call|makausap|kausap|kumausap|makipag)"
_TARGETS = r"(admin|agent|human|person|representative|staff|support|operator|owner|tao|customer service)"


def wants_human(question):
    text = (question or "").lower()
    if re.search(r"\blive\s*chat\b|\breal\s+(person|human)\b|\bhuman\s+agent\b", text):
        return True
    return bool(re.search(rf"\b{_VERBS}\b.*\b{_TARGETS}\b", text))


def _recent_unresolved(user_id, current_log_id):
    if not user_id:
        return 0
    query = ChatLog.query.filter(ChatLog.user_id == user_id)
    if current_log_id:
        query = query.filter(ChatLog.id < current_log_id)
    previous = query.order_by(ChatLog.id.desc()).limit(2).all()
    return sum(1 for log in previous if not log.resolved)


def suggest(question, result, user_id, current_log_id=None):
    """Returns {"needsHuman": bool, "humanReason": str|None, "humanMessage": str|None}."""
    none = {"needsHuman": False, "humanReason": None, "humanMessage": None}

    if wants_human(question):
        return {"needsHuman": True, "humanReason": "requested", "humanMessage": REQUESTED_MESSAGE}

    source = result.get("source")
    if source == "smalltalk" or result.get("resolved"):
        return none

    # An incomplete answer: a clarifying question, or no good match at all.
    unresolved_now = 1 + _recent_unresolved(user_id, current_log_id)
    if unresolved_now >= 2:
        return {"needsHuman": True, "humanReason": "repeated", "humanMessage": REPEATED_MESSAGE}
    if source == "fallback" and not result.get("related"):
        return {"needsHuman": True, "humanReason": "no_answer", "humanMessage": NO_ANSWER_MESSAGE}
    return none  # it still has related answers to offer, so let the customer try those first
