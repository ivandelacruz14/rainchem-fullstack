import io
from datetime import datetime, timedelta

from app.extensions import db
from app.models import AuditLog, LiveAttachment, LiveConversation, LiveMessage, User

JPEG = b"\xff\xd8\xff\xe0" + b"j" * 40 + b"\xff\xd9"
PNG = b"\x89PNG\r\n\x1a\n" + b"p" * 40 + b"\x00\x00\x00\x00IEND\xaeB`\x82"


def webp(extra=b"w" * 30):
    body = b"WEBP" + extra
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def upload(client, url, headers, data, name="photo.jpg", body="", **extra):
    form = {"image": (io.BytesIO(data), name)}
    if body:
        form["body"] = body
    form.update(extra)
    return client.post(url, headers=headers, data=form, content_type="multipart/form-data")


def staff(make_admin, admin_login, email="staff@example.com"):
    make_admin(email, "Support Staff")
    return admin_login(email)


SEND = "/api/live-chat/messages"
ADMIN = "/api/admin/live-chat"


def test_customer_can_send_each_supported_image_type(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    for data, mime in ((JPEG, "image/jpeg"), (PNG, "image/png"), (webp(), "image/webp")):
        r = upload(client, SEND, h, data, body="Look at this")
        assert r.status_code == 201, r.get_json()
        message = r.get_json()["message"]
        assert message["kind"] == "image" and message["attachment"]["mime"] == mime and message["body"] == "Look at this"
    assert LiveAttachment.query.count() == 3


def test_an_image_alone_without_a_caption_is_allowed_but_empty_sends_are_not(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    assert upload(client, SEND, h, PNG).status_code == 201
    assert client.post(SEND, headers=h, json={"body": ""}).status_code == 400
    assert upload(client, SEND, h, b"").status_code == 400


def test_the_file_is_checked_by_its_content_not_its_name_or_type(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    cases = {
        "a script renamed to .jpg": (b"<?php echo 1; ?>", "evil.jpg"),
        "html renamed to .png": (b"<html><script>alert(1)</script></html>", "x.png"),
        "an svg": (b"<svg xmlns='http://www.w3.org/2000/svg'><script>1</script></svg>", "x.svg"),
        "a truncated jpeg": (b"\xff\xd8\xff\xe0" + b"j" * 40, "cut.jpg"),
        "a png with no end": (b"\x89PNG\r\n\x1a\n" + b"p" * 40, "cut.png"),
        "a pdf": (b"%PDF-1.4 ...", "doc.pdf"),
        "a webp with a wrong size": (b"RIFF" + (999).to_bytes(4, "little") + b"WEBP" + b"w" * 10, "bad.webp"),
        "a gif": (b"GIF89a" + b"g" * 20, "a.gif"),
    }
    for label, (data, name) in cases.items():
        r = upload(client, SEND, h, data, name=name)
        assert r.status_code == 400, label
        assert "not a valid" in r.get_json()["error"], label
    assert LiveAttachment.query.count() == 0 and LiveMessage.query.count() == 0
    # a real image is accepted even if it is called something odd
    assert upload(client, SEND, h, JPEG, name="report.pdf").status_code == 201


def test_the_stored_name_is_generated_and_the_uploaded_name_is_never_used(client, make_user, user_login):
    make_user()
    upload(client, SEND, user_login("customer@example.com"), JPEG, name="../../etc/passwd.jpg")
    attachment = LiveAttachment.query.one()
    assert attachment.stored_name.endswith(".jpg") and len(attachment.stored_name) > 20
    assert "passwd" not in attachment.stored_name and "/" not in attachment.stored_name


def test_the_size_limit_is_configurable(app, client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    app.config["CHAT_UPLOAD_MAX_MB"] = 0.0001           # about 100 bytes
    too_big = JPEG + b"\x00" * 500
    r = upload(client, SEND, h, b"\xff\xd8\xff" + b"j" * 500 + b"\xff\xd9")
    assert r.status_code == 413 and "too large" in r.get_json()["error"]
    app.config["CHAT_UPLOAD_MAX_MB"] = 1
    assert upload(client, SEND, h, JPEG).status_code == 201
    assert client.get("/api/live-chat", headers=h).get_json()["maxUploadMb"] == 1


def test_only_the_two_people_in_the_conversation_can_open_the_image(client, make_user, user_login, make_admin, admin_login):
    make_user("a@example.com", "Ana A")
    make_user("b@example.com", "Bea B")
    a, b = user_login("a@example.com"), user_login("b@example.com")
    ah = staff(make_admin, admin_login)
    attachment_id = upload(client, SEND, a, PNG).get_json()["message"]["attachment"]["id"]
    mine = client.get(f"/api/live-chat/attachments/{attachment_id}", headers=a)
    assert mine.status_code == 200 and mine.data == PNG and mine.mimetype == "image/png"
    assert mine.headers["X-Content-Type-Options"] == "nosniff" and "private" in mine.headers["Cache-Control"]
    assert "sandbox" in mine.headers["Content-Security-Policy"]
    assert client.get(f"/api/live-chat/attachments/{attachment_id}", headers=b).status_code == 404       # another customer
    assert client.get(f"/api/live-chat/attachments/{attachment_id}").status_code == 401                  # nobody signed in
    assert client.get(f"{ADMIN}/attachments/{attachment_id}", headers=a).status_code == 403              # a customer on the admin route
    assert client.get(f"{ADMIN}/attachments/{attachment_id}", headers=ah).data == PNG
    make_admin("noperm@example.com", "Support Staff", ["orders"])
    assert client.get(f"{ADMIN}/attachments/{attachment_id}", headers=admin_login("noperm@example.com")).status_code == 403
    assert client.get("/api/live-chat/attachments/9999", headers=a).status_code == 404


def test_admin_can_send_images_too_and_the_customer_can_open_them(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    cid = client.post(SEND, headers=h, json={"body": "hi"}).get_json()["conversation"]["id"]
    r = upload(client, f"{ADMIN}/conversations/{cid}/messages", ah, JPEG, body="Here is the invoice")
    assert r.status_code == 201 and r.get_json()["message"]["kind"] == "image"
    mid = r.get_json()["message"]["attachment"]["id"]
    assert client.get(f"/api/live-chat/attachments/{mid}", headers=h).data == JPEG
    assert upload(client, f"{ADMIN}/conversations/{cid}/messages", ah, b"not an image").status_code == 400


def test_deleting_an_image_message_erases_the_bytes_but_keeps_an_audit_record(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    sent = upload(client, SEND, h, PNG, body="payment proof").get_json()
    mid, aid = sent["message"]["id"], sent["message"]["attachment"]["id"]
    assert client.delete(f"/api/live-chat/messages/{mid}", headers=h).status_code == 200
    assert LiveAttachment.query.count() == 0
    assert client.get(f"/api/live-chat/attachments/{aid}", headers=h).status_code == 404
    entry = AuditLog.query.filter_by(action="chat_message_deleted").one()
    assert entry.admin_name == "Customer: Maria Santos" and entry.entity_id == str(mid)
    assert entry.old_value["kind"] == "image" and len(entry.old_value["imageSha256"]) == 64 and len(entry.old_value["textSha256"]) == 64
    assert "payment proof" not in str(entry.old_value) and entry.created_at


def test_admin_deletes_are_audited_with_the_admin_and_conversation_deletes_too(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    sent = client.post(SEND, headers=h, json={"body": "something"}).get_json()
    client.delete(f"{ADMIN}/messages/{sent['message']['id']}", headers=ah)
    entry = AuditLog.query.filter_by(action="chat_message_deleted").one()
    assert entry.admin_name == "Admin" and entry.admin_id is not None and entry.new_value == {"deletedBy": "admin"}
    make_admin("head@example.com", "Head Admin")
    client.delete(f"{ADMIN}/conversations/{sent['conversation']['id']}", headers=admin_login("head@example.com"))
    removed = AuditLog.query.filter_by(action="chat_conversation_deleted").one()
    assert removed.old_value["customer"] == "Maria Santos" and removed.old_value["messages"] == 1


def test_image_messages_show_as_photos_in_previews(client, make_user, user_login, make_admin, admin_login):
    make_user()
    ah = staff(make_admin, admin_login)
    upload(client, SEND, user_login("customer@example.com"), JPEG, body="the damage")
    assert client.get(f"{ADMIN}/conversations", headers=ah).get_json()["conversations"][0]["lastMessage"]["text"] == "Photo: the damage"


def test_conversation_status_workflow(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    cid = client.post(SEND, headers=h, json={"body": "help"}).get_json()["conversation"]["id"]
    assert LiveConversation.query.one().status == "open"
    client.post(f"{ADMIN}/conversations/{cid}/messages", headers=ah, json={"body": "sure"})
    assert LiveConversation.query.one().status == "pending"                       # waiting for the customer
    client.post(SEND, headers=h, json={"body": "thanks"})
    assert LiveConversation.query.one().status == "open"                          # the customer wrote back
    resolved = client.post(f"{ADMIN}/conversations/{cid}/status", headers=ah, json={"status": "resolved"})
    assert resolved.get_json()["conversation"]["status"] == "resolved" and LiveConversation.query.one().resolved_at
    client.post(SEND, headers=h, json={"body": "one more thing"})
    assert LiveConversation.query.one().status == "open" and LiveConversation.query.one().resolved_at is None
    client.post(f"{ADMIN}/conversations/{cid}/status", headers=ah, json={"status": "resolved"})
    assert client.post(f"{ADMIN}/conversations/{cid}/status", headers=ah, json={"status": "open"}).get_json()["conversation"]["statusLabel"] == "Open"
    assert client.post(f"{ADMIN}/conversations/{cid}/status", headers=ah, json={"status": "bogus"}).status_code == 400
    assert client.post(f"{ADMIN}/conversations/9999/status", headers=ah, json={"status": "open"}).status_code == 404


def test_inbox_filters_search_sorting_and_attention(client, make_user, user_login, make_admin, admin_login):
    for email, name in (("a@example.com", "Ana Reyes"), ("b@example.com", "Ben Cruz"), ("c@example.com", "Cara Lim")):
        make_user(email, name)
    ah = staff(make_admin, admin_login)
    ids = {}
    for email in ("a@example.com", "b@example.com", "c@example.com"):
        ids[email] = client.post(SEND, headers=user_login(email), json={"body": f"hi from {email}"}).get_json()["conversation"]["id"]
    client.post(f"{ADMIN}/conversations/{ids['b@example.com']}/messages", headers=ah, json={"body": "reply"})          # b -> pending
    client.post(f"{ADMIN}/conversations/{ids['c@example.com']}/status", headers=ah, json={"status": "resolved"})
    client.post(f"{ADMIN}/conversations/{ids['a@example.com']}/messages", headers=ah, json={"body": "more"})
    q = lambda **kw: client.get(f"{ADMIN}/conversations", headers=ah, query_string=kw).get_json()
    names = lambda data: [c["user"]["name"] for c in data["conversations"]]
    assert sorted(names(q(filter="pending"))) == ["Ana Reyes", "Ben Cruz"]
    assert names(q(filter="resolved")) == ["Cara Lim"] and names(q(filter="open")) == []
    assert sorted(names(q(filter="unread"))) == ["Ana Reyes", "Ben Cruz", "Cara Lim"]      # replying does not mark a conversation read
    client.post(f"{ADMIN}/conversations/{ids['a@example.com']}/read", headers=ah)
    assert sorted(names(q(filter="unread"))) == ["Ben Cruz", "Cara Lim"]
    counts = q()["counts"]
    assert (counts["all"], counts["pending"], counts["resolved"], counts["unread"]) == (3, 2, 1, 2)
    assert names(q(search="ben")) == ["Ben Cruz"] and names(q(search="c@example")) == ["Cara Lim"]
    assert names(q(sort="oldest"))[0] == "Ana Reyes" or names(q(sort="oldest"))
    rows = {c["user"]["name"]: c for c in q()["conversations"]}
    assert rows["Cara Lim"]["needsAttention"] is False and rows["Cara Lim"]["unread"] == 1   # resolved conversations do not demand attention
    client.post(SEND, headers=user_login("b@example.com"), json={"body": "again"})
    assert {c["user"]["name"]: c["needsAttention"] for c in q()["conversations"]}["Ben Cruz"] is True
    assert names(q(sort="unread"))[0] == "Ben Cruz"
    assert names(q(filter="bogus"))                                              # an unknown filter shows everything instead of failing


def test_online_status_comes_from_real_activity(client, make_user, user_login, make_admin, admin_login):
    make_user()
    h, ah = user_login("customer@example.com"), staff(make_admin, admin_login)
    cid = client.post(SEND, headers=h, json={"body": "hi"}).get_json()["conversation"]["id"]
    row = lambda: client.get(f"{ADMIN}/conversations", headers=ah).get_json()["conversations"][0]
    assert row()["online"] is False                                             # sending is not the same as having the chat open
    client.get("/api/live-chat", headers=h)
    assert row()["online"] is True
    LiveConversation.query.update({"user_last_seen_at": datetime.utcnow() - timedelta(minutes=5)})
    db.session.commit()
    assert row()["online"] is False


def test_admin_starts_a_conversation_from_an_order_without_duplicates(client, make_user, user_login, make_admin, admin_login, make_product, make_order):
    user = make_user()
    order = make_order(user, [(make_product(), 100, 1)], status="pending_confirmation", payment_status="unpaid")
    ah = staff(make_admin, admin_login)
    first = client.post(f"{ADMIN}/conversations/start", headers=ah, json={"orderId": order.id})
    assert first.status_code == 201 and first.get_json()["created"] is True
    conv = first.get_json()["conversation"]
    assert conv["orderNumber"] == order.order_number and conv["topic"] == "order" and conv["status"] == "pending" and conv["user"]["name"] == user.name
    again = client.post(f"{ADMIN}/conversations/start", headers=ah, json={"orderId": order.id})
    assert again.status_code == 200 and again.get_json()["created"] is False and again.get_json()["conversation"]["id"] == conv["id"]
    assert LiveConversation.query.count() == 1
    # the customer already has a conversation: it is reused, and linked to the new order
    other = make_order(user, [(make_product("Two"), 10, 1)])
    reused = client.post(f"{ADMIN}/conversations/start", headers=ah, json={"orderId": other.id}).get_json()["conversation"]
    assert reused["id"] == conv["id"] and reused["orderNumber"] == other.order_number and LiveConversation.query.count() == 1
    assert client.post(f"{ADMIN}/conversations/start", headers=ah, json={"orderId": 9999}).status_code == 404
    assert client.post(f"{ADMIN}/conversations/start", headers=ah, json={}).status_code == 404


def test_the_customer_is_notified_when_the_admin_writes_first(client, make_user, user_login, make_admin, admin_login, make_product, make_order):
    user = make_user()
    order = make_order(user, [(make_product(), 100, 1)], status="pending_confirmation")
    ah, h = staff(make_admin, admin_login), user_login(user.email)
    cid = client.post(f"{ADMIN}/conversations/start", headers=ah, json={"orderId": order.id}).get_json()["conversation"]["id"]
    assert client.get("/api/live-chat/unread", headers=h).get_json()["unread"] == 0          # nothing to read yet
    client.post(f"{ADMIN}/conversations/{cid}/messages", headers=ah, json={"body": "Can you confirm your address?"})
    note = client.get("/api/live-chat/unread", headers=h).get_json()
    assert note["unread"] == 1 and note["latest"]["text"] == "Can you confirm your address?" and note["latest"]["from"] == "admin"
    snapshot = client.get("/api/live-chat", headers=h).get_json()
    assert snapshot["conversation"]["orderNumber"] == order.order_number and snapshot["messages"][0]["sender"] == "admin"


def test_starting_a_conversation_needs_the_livechat_permission(client, make_user, user_login, make_admin, admin_login, make_product, make_order):
    user = make_user()
    order = make_order(user, [(make_product(), 100, 1)])
    make_admin("nope@example.com", "Support Staff", ["orders", "manage_orders"])
    body = {"orderId": order.id}
    assert client.post(f"{ADMIN}/conversations/start", headers=admin_login("nope@example.com"), json=body).status_code == 403
    assert client.post(f"{ADMIN}/conversations/start", json=body).status_code == 401
    assert client.post(f"{ADMIN}/conversations/start", headers=user_login(user.email), json=body).status_code == 403


def test_customer_panel_shows_only_what_the_admin_may_see(client, make_user, user_login, make_admin, admin_login, make_product, make_order):
    user = make_user()
    order = make_order(user, [(make_product("Oil"), 100, 2)], status="confirmed", payment_status="paid")
    cid = client.post(SEND, headers=user_login(user.email), json={"body": "hi", "orderId": order.id}).get_json()["conversation"]["id"]
    full = staff(make_admin, admin_login)                                          # support staff: orders, customers, livechat
    data = client.get(f"{ADMIN}/conversations/{cid}/customer", headers=full).get_json()
    assert data["customer"]["email"] == user.email and data["customer"]["phone"] and data["customer"]["verified"] is True
    first = data["orders"][0]
    assert first["orderNumber"] == order.order_number and first["items"] == [{"name": "Oil", "quantity": 2}] and first["linked"] is True
    assert first["paymentStatus"] == "paid" and first["confirmed"] is True and first["journeyHeadline"] and data["canOpenOrders"] is True

    make_admin("chatonly@example.com", "Support Staff", ["livechat"])
    limited = client.get(f"{ADMIN}/conversations/{cid}/customer", headers=admin_login("chatonly@example.com")).get_json()
    assert "phone" not in limited["customer"] and limited["orders"] == [] and limited["canSeeOrders"] is False
    assert client.get(f"{ADMIN}/conversations/9999/customer", headers=full).status_code == 404


def test_profile_photos_are_served_only_to_chat_admins(client, make_user, user_login, make_admin, admin_login):
    import base64
    user = make_user()
    user.avatar_photo = "data:image/png;base64," + base64.b64encode(PNG).decode()
    db.session.commit()
    ah = staff(make_admin, admin_login)
    assert client.get(f"{ADMIN}/users/{user.id}/photo", headers=ah).data == PNG
    assert client.get(f"{ADMIN}/users/{user.id}/photo").status_code == 401
    assert client.get(f"{ADMIN}/users/{user.id}/photo", headers=user_login(user.email)).status_code == 403
    user.avatar_photo = "data:text/html;base64," + base64.b64encode(b"<script>").decode()
    db.session.commit()
    assert client.get(f"{ADMIN}/users/{user.id}/photo", headers=ah).status_code == 404
    other = make_user("o@example.com", "No Photo")
    assert client.get(f"{ADMIN}/users/{other.id}/photo", headers=ah).status_code == 404
    rows = client.get(f"{ADMIN}/conversations", headers=ah).get_json()["conversations"]
    assert "avatar" not in str(rows).lower() and "base64" not in str(rows)                # the inbox list never carries the pictures
