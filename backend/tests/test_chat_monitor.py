from datetime import datetime, timedelta

from app.extensions import db
from app.models import ChatLog, KnowledgeEntry, LiveConversation, LiveMessage, Order, Product, User


def logs(make_user):
    user = make_user()
    entry = KnowledgeEntry(question="Payments?", answer="GCash", category="Payments", status="approved", hits=3)
    db.session.add(entry)
    db.session.flush()
    now = datetime.utcnow()
    rows = [
        ChatLog(question="What payment methods?", answer="GCash", confidence=90, resolved=True, user_id=user.id, matched_knowledge_id=entry.id, created_at=now - timedelta(minutes=3)),
        ChatLog(question="Do you sell chain lube?", answer="Not sure", confidence=10, resolved=False, user_id=user.id, created_at=now - timedelta(minutes=2)),
        ChatLog(question="Can you ship to Cebu tomorrow?", answer="Not sure", confidence=5, resolved=False, user_id=user.id, created_at=now - timedelta(minutes=1)),
    ]
    db.session.add_all(rows)
    db.session.commit()
    return user, entry, rows


def test_lists_unanswered_questions_with_stats(client, make_admin, admin_login, make_user):
    user, entry, rows = logs(make_user)
    make_admin()
    h = admin_login("head@example.com")
    data = client.get("/api/admin/chat-monitor?view=unanswered", headers=h).get_json()
    assert [l["question"] for l in data["logs"]] == ["Can you ship to Cebu tomorrow?", "Do you sell chain lube?"]
    assert data["logs"][0]["user"]["name"] == user.name
    assert data["stats"]["total"] == 3 and data["stats"]["unanswered"] == 2 and data["stats"]["resolved"] == 1
    assert len(client.get("/api/admin/chat-monitor?resolved=true", headers=h).get_json()["logs"]) == 1   # old filter still works
    assert [l["question"] for l in client.get("/api/admin/chat-monitor?search=lube", headers=h).get_json()["logs"]] == ["Do you sell chain lube?"]


def test_admin_sees_the_question_the_answer_and_the_conversation_around_it(client, make_admin, admin_login, make_user):
    user, entry, rows = logs(make_user)
    stranger = make_user("s@example.com", "Stranger Person")
    db.session.add(ChatLog(question="someone else", answer="x", confidence=1, resolved=False, user_id=stranger.id))
    db.session.commit()
    make_admin()
    detail = client.get(f"/api/admin/chat-monitor/{rows[1].id}", headers=admin_login("head@example.com")).get_json()
    assert detail["log"]["answer"] == "Not sure"
    assert [c["question"] for c in detail["context"]] == ["What payment methods?", "Can you ship to Cebu tomorrow?"]
    assert detail["hasLiveChat"] is False
    matched = client.get(f"/api/admin/chat-monitor/{rows[0].id}", headers=admin_login("head@example.com")).get_json()
    assert matched["matchedQuestion"] == "Payments?"
    assert client.get("/api/admin/chat-monitor/99999", headers=admin_login("head@example.com")).status_code == 404


def test_mark_resolved_and_reopen_without_touching_the_ai_flag(client, make_admin, admin_login, make_user):
    user, entry, rows = logs(make_user)
    make_admin()
    h = admin_login("head@example.com")
    r = client.post(f"/api/admin/chat-monitor/{rows[1].id}/resolve", headers=h, json={"resolved": True}).get_json()["log"]
    assert r["adminResolved"] is True and r["resolved"] is False                                       # the AI's own flag is unchanged
    assert [l["question"] for l in client.get("/api/admin/chat-monitor?view=unanswered", headers=h).get_json()["logs"]] == ["Can you ship to Cebu tomorrow?"]
    assert len(client.get("/api/admin/chat-monitor?view=resolved", headers=h).get_json()["logs"]) == 2
    assert client.post(f"/api/admin/chat-monitor/{rows[1].id}/resolve", headers=h, json={"resolved": False}).get_json()["log"]["adminResolved"] is False


def test_deleting_one_record_leaves_everything_else_alone(client, make_admin, admin_login, make_user, make_product, make_order):
    user, entry, rows = logs(make_user)
    order = make_order(user, [(make_product(), 100, 1)])
    live = LiveConversation(user_id=user.id, topic="ai")
    db.session.add(live)
    db.session.flush()
    db.session.add(LiveMessage(conversation_id=live.id, sender_type="user", sender_name=user.name, body="hello"))
    db.session.commit()
    make_admin()
    h = admin_login("head@example.com")

    assert client.delete(f"/api/admin/chat-monitor/{rows[1].id}", headers=h).status_code == 200
    assert db.session.get(ChatLog, rows[1].id) is None
    assert ChatLog.query.count() == 2                                   # only that record
    assert KnowledgeEntry.query.count() == 1 and db.session.get(KnowledgeEntry, entry.id).hits == 3
    assert Order.query.count() == 1 and Product.query.count() == 1 and User.query.count() == 1
    assert LiveConversation.query.count() == 1 and LiveMessage.query.count() == 1
    assert client.delete(f"/api/admin/chat-monitor/{rows[1].id}", headers=h).status_code == 404


def test_only_authorised_admins_can_use_the_monitor(client, make_admin, admin_login, make_user, user_login):
    user, entry, rows = logs(make_user)
    make_admin("dist@example.com", "Distributor", ["products"])
    make_admin("staff@example.com", "Support Staff")
    make_admin("content@example.com", "Content Manager")
    d = admin_login("dist@example.com")
    for method, url in [("get", "/api/admin/chat-monitor"), ("get", f"/api/admin/chat-monitor/{rows[0].id}"),
                        ("post", f"/api/admin/chat-monitor/{rows[0].id}/resolve"), ("delete", f"/api/admin/chat-monitor/{rows[0].id}")]:
        assert getattr(client, method)(url, headers=d).status_code == 403, url
        assert getattr(client, method)(url).status_code == 401, url
        assert getattr(client, method)(url, headers=user_login(user.email)).status_code == 403, url
    assert client.delete(f"/api/admin/chat-monitor/{rows[0].id}", headers=admin_login("staff@example.com")).status_code == 200   # chatbot permission
    assert ChatLog.query.count() == 2
