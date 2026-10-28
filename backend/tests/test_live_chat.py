from datetime import datetime, timedelta

from app.extensions import db
from app.models import LiveConversation, LiveMessage, User


def send(client, h, body="Hello", **extra):
    return client.post("/api/live-chat/messages", headers=h, json={"body": body, **extra})


def admin_reply(client, ah, conversation_id, body="Hi, how can I help?"):
    return client.post(f"/api/admin/live-chat/conversations/{conversation_id}/messages", headers=ah, json={"body": body})


def staff(make_admin, admin_login, email="staff@example.com"):
    make_admin(email, "Support Staff")  # starts with the livechat permission
    return admin_login(email)


def test_message_status_goes_sent_delivered_read(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    sent = send(client, h, "Where is my order?", topic="order")
    assert sent.status_code == 201 and sent.get_json()["message"]["status"] == "sent"    # 1 check
    cid = sent.get_json()["conversation"]["id"]

    inbox = client.get("/api/admin/live-chat/conversations", headers=ah).get_json()["conversations"]
    assert inbox[0]["unread"] == 1 and inbox[0]["user"]["name"] == "Maria Santos"
    assert inbox[0]["lastMessage"]["text"] == "Where is my order?"
    mine = client.get("/api/live-chat", headers=h).get_json()["messages"]
    assert mine[0]["status"] == "delivered"                                              # 2 checks once the admin's inbox has it

    client.get(f"/api/admin/live-chat/conversations/{cid}", headers=ah)
    assert client.post(f"/api/admin/live-chat/conversations/{cid}/read", headers=ah).get_json()["updated"] == 1
    mine = client.get("/api/live-chat", headers=h).get_json()["messages"]
    assert mine[0]["status"] == "read" and mine[0]["readAt"]                             # 2 coloured checks
    assert client.get("/api/admin/live-chat/conversations", headers=ah).get_json()["conversations"][0]["unread"] == 0


def test_admin_messages_use_the_same_statuses_for_the_customer(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    cid = send(client, h).get_json()["conversation"]["id"]
    reply = admin_reply(client, ah, cid)
    assert reply.status_code == 201 and reply.get_json()["message"]["status"] == "sent"
    assert client.get("/api/live-chat/unread", headers=h).get_json()["unread"] == 1       # fetching the badge delivers it
    admin_view = client.get(f"/api/admin/live-chat/conversations/{cid}", headers=ah).get_json()["messages"]
    assert [m["status"] for m in admin_view if m["sender"] == "admin"] == ["delivered"]
    assert client.post("/api/live-chat/read", headers=h).get_json()["updated"] == 1
    admin_view = client.get(f"/api/admin/live-chat/conversations/{cid}", headers=ah).get_json()["messages"]
    assert [m["status"] for m in admin_view if m["sender"] == "admin"] == ["read"]
    assert client.get("/api/live-chat/unread", headers=h).get_json()["unread"] == 0


def test_polling_returns_only_what_changed(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    first = send(client, h, "one").get_json()["message"]
    snapshot = client.get("/api/live-chat", headers=h).get_json()
    cursor = max(m["updatedAt"] for m in snapshot["messages"])
    assert client.get(f"/api/live-chat?since={cursor}", headers=h).get_json()["messages"][0]["id"] == first["id"]  # boundary is inclusive
    LiveMessage.query.update({"updated_at": datetime.utcnow() - timedelta(minutes=5)})
    db.session.commit()
    now = datetime.utcnow().isoformat()
    assert client.get(f"/api/live-chat?since={now}", headers=h).get_json()["messages"] == []
    cid = snapshot["conversation"]["id"]
    admin_reply(client, ah, cid, "two")
    changed = client.get(f"/api/live-chat?since={now}", headers=h).get_json()["messages"]
    assert [m["body"] for m in changed] == ["two"]
    assert client.get("/api/live-chat?since=garbage", headers=h).status_code == 400


def test_one_conversation_per_customer_is_reused(client, make_user, user_login, make_order, make_product):
    user = make_user()
    h = user_login(user.email)
    order = make_order(user, [(make_product(), 100, 1)])
    a = send(client, h, "first", topic="product")
    b = send(client, h, "second", topic="order", orderId=order.id)
    assert a.get_json()["conversation"]["id"] == b.get_json()["conversation"]["id"]
    assert LiveConversation.query.count() == 1 and LiveMessage.query.count() == 2
    info = b.get_json()["conversation"]
    assert info["topic"] == "order" and info["orderNumber"] == order.order_number


def test_who_may_chat(client, make_user, user_login):
    assert client.post("/api/live-chat/messages", json={"body": "hi"}).status_code == 401
    assert client.get("/api/live-chat").status_code == 401
    account = make_user("new@example.com")
    h = user_login("new@example.com")          # unverified accounts cannot log in at all; this one loses its
    account.verified = False                   # verified status after signing in, and the chat still refuses it
    db.session.commit()
    r = send(client, h)
    assert r.status_code == 403 and r.get_json()["code"] == "not_verified"
    assert LiveConversation.query.count() == 0


def test_validation_and_rate_limit(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    assert send(client, h, "   ").status_code == 400
    assert send(client, h, "x" * 2001).status_code == 400
    other = make_user("other@example.com", "Other Person")
    from app.models import Order
    assert send(client, h, "about an order", orderId=99999).status_code == 400
    assert LiveConversation.query.count() == 0
    for i in range(20):
        assert send(client, h, f"m{i}").status_code == 201
    assert send(client, h, "one too many").status_code == 429


def test_cannot_use_another_customers_order_in_chat(client, make_user, user_login, make_order, make_product):
    owner = make_user("owner@example.com", "Owner One")
    make_user()
    order = make_order(owner, [(make_product(), 100, 1)])
    assert send(client, user_login("customer@example.com"), "mine?", orderId=order.id).status_code == 400


def test_customers_only_ever_see_their_own_conversation(client, make_user, user_login):
    make_user("a@example.com", "Ana A")
    make_user("b@example.com", "Bea B")
    a, b = user_login("a@example.com"), user_login("b@example.com")
    send(client, a, "private to Ana")
    snapshot = client.get("/api/live-chat", headers=b).get_json()
    assert snapshot["conversation"] is None and snapshot["messages"] == []
    ids = [m["id"] for m in client.get("/api/live-chat", headers=a).get_json()["messages"]]
    assert client.delete(f"/api/live-chat/messages/{ids[0]}", headers=b).status_code == 404
    assert client.get("/api/admin/live-chat/conversations", headers=b).status_code == 403


def test_admin_access_needs_the_livechat_permission(client, make_admin, admin_login, make_user, user_login):
    make_user()
    cid = send(client, user_login("customer@example.com")).get_json()["conversation"]["id"]
    make_admin("dist@example.com", "Distributor", ["products", "orders"])
    make_admin("nopower@example.com", "Support Staff")
    from app.models import Admin
    db.session.query(Admin).filter_by(email="nopower@example.com").one().permissions = ["orders"]
    db.session.commit()
    for email in ("dist@example.com", "nopower@example.com"):
        h = admin_login(email)
        assert client.get("/api/admin/live-chat/conversations", headers=h).status_code == 403
        assert client.get(f"/api/admin/live-chat/conversations/{cid}", headers=h).status_code == 403
        assert client.post(f"/api/admin/live-chat/conversations/{cid}/messages", headers=h, json={"body": "x"}).status_code == 403
        assert client.get("/api/admin/live-chat/unread-count", headers=h).status_code == 403
    assert client.get("/api/admin/live-chat/conversations").status_code == 401


def test_a_sender_can_delete_their_own_message_and_the_text_is_erased(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    sent = send(client, h, "my card number is oops").get_json()
    mid, cid = sent["message"]["id"], sent["conversation"]["id"]
    admin_msg = admin_reply(client, ah, cid, "hello").get_json()["message"]

    assert client.delete(f"/api/live-chat/messages/{admin_msg['id']}", headers=h).status_code == 403   # not theirs
    gone = client.delete(f"/api/live-chat/messages/{mid}", headers=h)
    assert gone.status_code == 200 and gone.get_json()["message"]["deleted"] is True
    assert gone.get_json()["message"]["body"] is None and gone.get_json()["message"]["status"] == "deleted"
    assert LiveMessage.query.get(mid).body == ""                                                       # really erased
    as_admin = client.get(f"/api/admin/live-chat/conversations/{cid}", headers=ah).get_json()["messages"]
    assert [m for m in as_admin if m["id"] == mid][0]["deleted"] is True                               # the admin sees the marker
    assert client.get("/api/admin/live-chat/conversations", headers=ah).get_json()["conversations"][0]["lastMessage"]["text"] == "hello"
    assert client.delete(f"/api/live-chat/messages/{mid}", headers=h).status_code == 200               # repeating is harmless


def test_delivered_and_read_messages_can_still_be_deleted_by_the_sender(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    sent = send(client, h, "already read").get_json()
    client.post(f"/api/admin/live-chat/conversations/{sent['conversation']['id']}/read", headers=ah)
    assert client.get("/api/live-chat", headers=h).get_json()["messages"][0]["status"] == "read"
    assert client.delete(f"/api/live-chat/messages/{sent['message']['id']}", headers=h).get_json()["message"]["status"] == "deleted"


def test_admin_can_delete_any_message_and_only_a_head_admin_deletes_a_conversation(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    sent = send(client, h, "rude message").get_json()
    cid = sent["conversation"]["id"]
    assert client.delete(f"/api/admin/live-chat/messages/{sent['message']['id']}", headers=ah).get_json()["message"]["deletedBy"] == "admin"
    assert client.delete(f"/api/admin/live-chat/messages/99999", headers=ah).status_code == 404

    assert client.delete(f"/api/admin/live-chat/conversations/{cid}", headers=ah).status_code == 403   # support staff cannot
    make_admin("head@example.com", "Head Admin")
    head = admin_login("head@example.com")
    assert client.delete(f"/api/admin/live-chat/conversations/{cid}", headers=head).status_code == 200
    assert LiveConversation.query.count() == 0 and LiveMessage.query.count() == 0
    assert db.session.get(User, 1) is not None                                                         # the customer is untouched
    assert client.delete(f"/api/admin/live-chat/conversations/{cid}", headers=head).status_code == 404


def test_inbox_shows_unread_counts_latest_message_and_search(client, make_user, user_login, make_admin, admin_login):
    make_user("a@example.com", "Ana Reyes")
    make_user("b@example.com", "Ben Cruz")
    a, b, ah = user_login("a@example.com"), user_login("b@example.com"), staff(make_admin, admin_login)
    send(client, a, "a1")
    send(client, a, "a2")
    send(client, b, "b1")
    rows = client.get("/api/admin/live-chat/conversations", headers=ah).get_json()["conversations"]
    assert [r["user"]["name"] for r in rows] == ["Ben Cruz", "Ana Reyes"]                              # newest first
    assert {r["user"]["name"]: r["unread"] for r in rows} == {"Ana Reyes": 2, "Ben Cruz": 1}
    assert client.get("/api/admin/live-chat/unread-count", headers=ah).get_json() == {"unread": 3, "conversations": 2}
    found = client.get("/api/admin/live-chat/conversations?search=ana", headers=ah).get_json()["conversations"]
    assert [r["user"]["name"] for r in found] == ["Ana Reyes"]
    cid = rows[1]["id"]
    client.post(f"/api/admin/live-chat/conversations/{cid}/read", headers=ah)
    assert client.get("/api/admin/live-chat/unread-count", headers=ah).get_json()["unread"] == 1
    assert admin_reply(client, ah, 9999).status_code == 404
    assert admin_reply(client, ah, cid, "   ").status_code == 400


def test_messages_carry_date_and_time(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    message = send(client, h).get_json()["message"]
    assert datetime.fromisoformat(message["createdAt"]) <= datetime.utcnow()


def test_ai_context_can_be_handed_to_the_admin_once(client, make_user, user_login, make_admin, admin_login):
    from app.models import ChatLog
    user = make_user()
    other = make_user("o@example.com", "Other Person")
    mine = ChatLog(question="Do you sell chain lube?", answer="Sorry, not sure.", confidence=12, resolved=False, user_id=user.id)
    theirs = ChatLog(question="secret", answer="x", confidence=0, resolved=False, user_id=other.id)
    db.session.add_all([mine, theirs])
    db.session.commit()
    h, ah = user_login(user.email), staff(make_admin, admin_login)

    assert client.post("/api/live-chat/from-ai", headers=h, json={"logIds": [theirs.id]}).status_code == 400   # not their log
    assert client.post("/api/live-chat/from-ai", headers=h, json={"logIds": []}).status_code == 400
    r = client.post("/api/live-chat/from-ai", headers=h, json={"logIds": [mine.id]})
    assert r.status_code == 201 and r.get_json()["message"]["kind"] == "context"
    assert "chain lube" in r.get_json()["message"]["body"] and "secret" not in r.get_json()["message"]["body"]
    again = client.post("/api/live-chat/from-ai", headers=h, json={"logIds": [mine.id]})
    assert again.status_code == 200 and again.get_json()["alreadySent"] is True
    assert LiveMessage.query.count() == 1
    assert db.session.get(ChatLog, mine.id).handed_off_at is not None
    assert client.get("/api/admin/live-chat/conversations", headers=ah).get_json()["conversations"][0]["topic"] == "ai"
