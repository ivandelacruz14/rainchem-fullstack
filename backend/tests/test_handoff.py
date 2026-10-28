from app.extensions import db
from app.models import ChatLog, KnowledgeEntry
from app.services import handoff


def ask(client, h, question, **extra):
    r = client.post("/api/chat/ask", headers=h, json={"question": question, **extra})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def seed_kb():
    db.session.add(KnowledgeEntry(question="What payment methods do you accept?", answer="GCash, card and cash on delivery.",
                                  category="Payments", status="approved"))
    db.session.commit()


def test_a_good_answer_does_not_suggest_a_person(client, make_user, user_login):
    seed_kb()
    make_user()
    result = ask(client, user_login("customer@example.com"), "What payment methods do you accept?")
    assert result["resolved"] is True and result["needsHuman"] is False and result["humanMessage"] is None


def test_small_talk_never_suggests_a_person(client, make_user, user_login):
    make_user()
    assert ask(client, user_login("customer@example.com"), "hello")["needsHuman"] is False


def test_no_usable_answer_suggests_the_admin_with_the_exact_wording(client, make_user, user_login):
    make_user()
    result = ask(client, user_login("customer@example.com"), "zxqv blorpf wibble quux")
    assert result["resolved"] is False and result["needsHuman"] is True and result["humanReason"] == "no_answer"
    assert result["humanMessage"] == ("I may not have enough information to answer your question accurately. "
                                      "Would you like to chat with our admin for further assistance?")


def test_an_unfamiliar_question_with_related_answers_is_not_called_unsolvable(client, make_user, user_login, monkeypatch):
    make_user()
    fake = {"answer": "I'm not sure. Did you mean one of these?", "source": "fallback", "resolved": False,
            "confidence": 30, "related": [{"id": 1, "question": "What payment methods do you accept?"}], "can_rate": True,
            "matched_entry": None}
    assert handoff.suggest("odd question", fake, user_id=None)["needsHuman"] is False


def test_repeated_incomplete_answers_suggest_the_admin_even_with_related_answers(app):
    fake = {"source": "fallback", "resolved": False, "related": [{"id": 1, "question": "x"}]}
    db.session.add(ChatLog(question="q1", answer="a", confidence=10, resolved=False, user_id=1))
    db.session.commit()
    result = handoff.suggest("another odd one", fake, user_id=1)
    assert result["needsHuman"] is True and result["humanReason"] == "repeated"


def test_unresolved_answers_of_other_customers_do_not_count(client, make_user, user_login):
    make_user()
    other = make_user("o@example.com", "Other Person")
    db.session.add(ChatLog(question="q", answer="a", confidence=0, resolved=False, user_id=other.id))
    db.session.commit()
    fake = {"source": "fallback", "resolved": False, "related": [{"id": 1, "question": "x"}]}
    assert handoff.suggest("odd", fake, user_id=1)["needsHuman"] is False


def test_asking_for_a_person_is_always_honoured(client, make_user, user_login):
    seed_kb()
    make_user()
    h = user_login("customer@example.com")
    for text in ["I want to talk to an admin", "can I speak with a real person", "live chat please",
                 "gusto kong makausap ang admin", "connect me to a human agent"]:
        result = ask(client, h, text)
        assert result["needsHuman"] is True and result["humanReason"] == "requested", text
    assert handoff.wants_human("What payment methods do you accept?") is False
    assert handoff.wants_human("my account was admin approved") is False


def test_a_low_rating_offers_the_admin(client, make_user, user_login):
    seed_kb()
    make_user()
    h = user_login("customer@example.com")
    log_id = ask(client, h, "What payment methods do you accept?")["logId"]
    low = client.post("/api/chat/feedback", headers=h, json={"logId": log_id, "rating": 1}).get_json()
    assert low["needsHuman"] is True and low["humanReason"] == "low_rating"
    high = client.post("/api/chat/feedback", headers=h, json={"logId": log_id, "rating": 5}).get_json()
    assert "needsHuman" not in high


def test_handoff_does_not_change_the_existing_answer_fields(client, make_user, user_login):
    seed_kb()
    make_user()
    result = ask(client, user_login("customer@example.com"), "What payment methods do you accept?")
    for key in ("logId", "answer", "confidence", "resolved", "source", "canRate", "related"):
        assert key in result
