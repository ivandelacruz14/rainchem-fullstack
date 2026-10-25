from datetime import datetime, timedelta

from app.extensions import db
from app.models import ApprovalOtp, ChangeRequest, Product
from conftest import PASSWORD, emailed_code

NEW_PRODUCT = {"name": "Fresh Oil", "category": "Oils & Fluids", "price": 450, "stock": 10, "shortDesc": "s", "description": "d"}


def setup(make_admin, admin_login, role="Distributor", perms=("products",)):
    make_admin()
    distributor = make_admin("d@example.com", role, list(perms))
    return admin_login("head@example.com"), admin_login("d@example.com"), distributor


def start(client, head, request_id, password=PASSWORD):
    return client.post(f"/api/admin/approvals/{request_id}/approve/start", headers=head, json={"password": password})


def confirm(client, head, request_id, code):
    return client.post(f"/api/admin/approvals/{request_id}/approve/confirm", headers=head, json={"code": code})


def test_head_admin_changes_apply_immediately(client, make_admin, admin_login, make_product):
    make_admin()
    h = admin_login("head@example.com")
    p = make_product("Old", price=100)
    assert client.post("/api/products", headers=h, json=NEW_PRODUCT).status_code == 201
    assert client.put(f"/api/products/{p.id}", headers=h, json={"name": "New name"}).status_code == 200
    assert client.delete(f"/api/products/{p.id}", headers=h).status_code == 200
    assert ChangeRequest.query.count() == 0


def test_non_head_changes_become_requests_and_change_nothing(client, make_admin, admin_login, make_product, mailbox):
    head, dist, d = setup(make_admin, admin_login)
    mine = make_product("Mine", price=100, owner=d)

    add = client.post("/api/products", headers=dist, json=NEW_PRODUCT)
    edit = client.put(f"/api/products/{mine.id}", headers=dist, json={"price": 1, "stock": 0})
    delete = client.delete(f"/api/products/{mine.id}", headers=dist)
    for r in (add, edit, delete):
        assert r.status_code == 202 and r.get_json()["pendingApproval"] is True

    assert Product.query.count() == 1
    refreshed = db.session.get(Product, mine.id)
    assert float(refreshed.price) == 100 and refreshed.stock == 50
    assert ChangeRequest.query.filter_by(status="pending").count() == 3
    assert any("Approval needed" in m["subject"] for m in mailbox)  # the Head Admin is told


def test_invalid_requests_are_refused_up_front(client, make_admin, admin_login, make_product):
    head, dist, d = setup(make_admin, admin_login)
    theirs = make_product("Theirs")
    assert client.post("/api/products", headers=dist, json={"name": "", "price": -1}).status_code == 400
    assert client.put(f"/api/products/{theirs.id}", headers=dist, json={"price": 5}).status_code == 403
    assert client.delete(f"/api/products/{theirs.id}", headers=dist).status_code == 403
    assert ChangeRequest.query.count() == 0


def test_visibility_requester_sees_own_head_sees_all(client, make_admin, admin_login):
    head, dist, d = setup(make_admin, admin_login)
    make_admin("other@example.com", "Distributor", ["products"])
    other = admin_login("other@example.com")
    req = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]
    assert len(client.get("/api/admin/approvals", headers=head).get_json()["requests"]) == 1
    assert len(client.get("/api/admin/approvals", headers=dist).get_json()["requests"]) == 1
    assert client.get("/api/admin/approvals", headers=other).get_json()["requests"] == []
    assert client.get(f"/api/admin/approvals/{req['id']}", headers=other).status_code == 404
    assert client.get("/api/admin/approvals/pending-count", headers=head).get_json()["count"] == 1
    assert client.get("/api/admin/approvals/pending-count", headers=other).get_json()["count"] == 0


def test_the_request_shows_what_would_change(client, make_admin, admin_login, make_product):
    head, dist, d = setup(make_admin, admin_login)
    mine = make_product("Mine", price=100, owner=d)
    client.put(f"/api/products/{mine.id}", headers=dist, json={"price": 80, "name": "Mine"})
    row = client.get("/api/admin/approvals?status=pending", headers=head).get_json()["requests"][0]
    assert row["kindLabel"] == "Edit product"
    assert row["changes"] == [{"field": "Price", "from": "100.00", "to": "80.00"}]  # unchanged name is not listed


def test_only_a_head_admin_can_approve_or_reject(client, make_admin, admin_login):
    head, dist, d = setup(make_admin, admin_login)
    rid = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]["id"]
    for url, body in [(f"/api/admin/approvals/{rid}/approve/start", {"password": PASSWORD}),
                      (f"/api/admin/approvals/{rid}/approve/confirm", {"code": "123456"}),
                      (f"/api/admin/approvals/{rid}/reject", {})]:
        assert client.post(url, headers=dist, json=body).status_code == 403, url
    assert client.post(f"/api/admin/approvals/{rid}/approve/start", json={}).status_code == 401
    assert Product.query.count() == 0


def test_approval_needs_the_password_first(client, make_admin, admin_login, mailbox):
    head, dist, d = setup(make_admin, admin_login)
    rid = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]["id"]
    mailbox.clear()
    assert start(client, head, rid, password="wrong").status_code == 403
    assert start(client, head, rid, password="").status_code == 403
    assert mailbox == []  # no code is sent to someone who did not prove their password
    assert ApprovalOtp.query.count() == 0


def test_full_approval_applies_an_add(client, make_admin, admin_login, mailbox):
    head, dist, d = setup(make_admin, admin_login)
    rid = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]["id"]
    mailbox.clear()
    started = start(client, head, rid)
    assert started.status_code == 200 and started.get_json()["email"].endswith("@example.com") and "*" in started.get_json()["email"]
    assert mailbox[0]["to"] == "head@example.com" and mailbox[0]["kwargs"]["sensitive"] is True
    code = emailed_code(mailbox)
    assert Product.query.count() == 0                      # still nothing until the code is confirmed
    assert confirm(client, head, rid, code).status_code == 200
    product = Product.query.one()
    assert product.name == "Fresh Oil" and product.owner_admin_id == d.id
    row = db.session.get(ChangeRequest, rid)
    assert row.status == "approved" and row.decider_name == "Admin" and row.decided_at
    assert any("approved" in m["subject"] for m in mailbox)  # the requester hears back


def test_approval_applies_an_edit_and_a_delete(client, make_admin, admin_login, make_product, approve):
    head, dist, d = setup(make_admin, admin_login)
    a, b = make_product("A", price=100, owner=d), make_product("B", price=100, owner=d)
    edit = client.put(f"/api/products/{a.id}", headers=dist, json={"price": 75, "stock": 7}).get_json()["request"]["id"]
    delete = client.delete(f"/api/products/{b.id}", headers=dist).get_json()["request"]["id"]
    assert approve(head, edit).status_code == 200
    assert approve(head, delete).status_code == 200
    assert float(db.session.get(Product, a.id).price) == 75 and db.session.get(Product, a.id).stock == 7
    assert db.session.get(Product, b.id) is None


def test_code_rules_wrong_expired_attempts_and_reuse(client, make_admin, admin_login, mailbox):
    head, dist, d = setup(make_admin, admin_login)
    rid = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]["id"]
    assert confirm(client, head, rid, "123456").status_code == 400            # no code asked for yet
    start(client, head, rid)
    code = emailed_code(mailbox)
    wrong = "000000" if code != "000000" else "111111"
    r = confirm(client, head, rid, wrong)
    assert r.status_code == 400 and "4 tries left" in r.get_json()["error"]
    for _ in range(4):
        confirm(client, head, rid, wrong)
    locked = confirm(client, head, rid, code)                                 # even the right code is refused now
    assert locked.status_code == 429 and Product.query.count() == 0

    ApprovalOtp.query.update({"created_at": datetime.utcnow() - timedelta(minutes=5)})
    db.session.commit()
    assert start(client, head, rid).status_code == 200
    fresh = emailed_code(mailbox)
    ApprovalOtp.query.filter_by(used=False).update({"expires_at": datetime.utcnow() - timedelta(seconds=1)})
    db.session.commit()
    assert "expired" in confirm(client, head, rid, fresh).get_json()["error"]

    ApprovalOtp.query.update({"created_at": datetime.utcnow() - timedelta(minutes=5)})
    db.session.commit()
    start(client, head, rid)
    good = emailed_code(mailbox)
    assert confirm(client, head, rid, good).status_code == 200
    assert confirm(client, head, rid, good).status_code == 409                # a used code cannot approve again
    assert Product.query.count() == 1


def test_the_code_is_stored_hashed_and_limited_per_request(client, make_admin, admin_login, mailbox):
    head, dist, d = setup(make_admin, admin_login)
    r1 = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]["id"]
    r2 = client.post("/api/products", headers=dist, json={**NEW_PRODUCT, "name": "Second"}).get_json()["request"]["id"]
    start(client, head, r1)
    code = emailed_code(mailbox)
    otp = ApprovalOtp.query.one()
    assert code not in (otp.code_hash, otp.salt) and len(otp.code_hash) == 64
    assert confirm(client, head, r2, code).status_code == 400                 # a code for one request cannot approve another
    assert start(client, head, r1).status_code == 429                         # slow down between codes
    assert Product.query.count() == 0


def test_if_the_email_cannot_be_sent_nothing_is_approved(client, make_admin, admin_login, monkeypatch):
    head, dist, d = setup(make_admin, admin_login)
    rid = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]["id"]
    monkeypatch.setattr("app.services.change_requests.send_email", lambda *a, **k: False)
    r = start(client, head, rid)
    assert r.status_code == 503 and "email" in r.get_json()["error"].lower()
    assert ApprovalOtp.query.filter_by(used=False).count() == 0
    assert db.session.get(ChangeRequest, rid).status == "pending"


def test_reject_and_cancel(client, make_admin, admin_login, mailbox):
    head, dist, d = setup(make_admin, admin_login)
    r1 = client.post("/api/products", headers=dist, json=NEW_PRODUCT).get_json()["request"]["id"]
    r2 = client.post("/api/products", headers=dist, json={**NEW_PRODUCT, "name": "Two"}).get_json()["request"]["id"]
    rejected = client.post(f"/api/admin/approvals/{r1}/reject", headers=head, json={"note": "Wrong price"})
    assert rejected.get_json()["request"]["status"] == "rejected" and rejected.get_json()["request"]["note"] == "Wrong price"
    assert client.post(f"/api/admin/approvals/{r1}/reject", headers=head, json={}).status_code == 409
    assert start(client, head, r1).status_code == 409
    assert client.post(f"/api/admin/approvals/{r2}/cancel", headers=dist).status_code == 200
    assert client.post(f"/api/admin/approvals/{r2}/cancel", headers=dist).status_code == 409
    assert client.post(f"/api/admin/approvals/{r2}/cancel", headers=head).status_code in (403, 409)
    assert Product.query.count() == 0


def test_a_stale_request_cannot_be_applied(client, make_admin, admin_login, make_product, approve):
    head, dist, d = setup(make_admin, admin_login)
    p = make_product("Mine", owner=d)
    edit = client.put(f"/api/products/{p.id}", headers=dist, json={"price": 5}).get_json()["request"]["id"]
    assert client.delete(f"/api/products/{p.id}", headers=head).status_code == 200    # head deletes it meanwhile
    r = approve(head, edit)
    assert r.status_code == 409 and "no longer exists" in r.get_json()["error"]
    assert db.session.get(ChangeRequest, edit).status == "pending"


def test_deleting_a_reviewed_product_is_blocked_at_request_time(client, make_admin, admin_login, make_product, make_user, make_order, user_login):
    head, dist, d = setup(make_admin, admin_login)
    p = make_product("Mine", owner=d)
    user = make_user()
    order = make_order(user, [(p, 100, 1)])
    client.post(f"/api/orders/{order.id}/reviews", headers=user_login(user.email), json={"reviews": [{"productId": p.id, "rating": 5}]})
    assert client.delete(f"/api/products/{p.id}", headers=dist).status_code == 409
    assert ChangeRequest.query.count() == 0


def test_photo_is_kept_out_of_lists_and_shown_in_detail(client, make_admin, admin_login):
    head, dist, d = setup(make_admin, admin_login)
    rid = client.post("/api/products", headers=dist, json={**NEW_PRODUCT, "imagePhoto": "data:image/png;base64,AAAA"}).get_json()["request"]["id"]
    listing = client.get("/api/admin/approvals", headers=head).get_json()["requests"][0]
    assert listing["hasPhoto"] is True and "photo" not in listing and "AAAA" not in str(listing)
    assert client.get(f"/api/admin/approvals/{rid}", headers=head).get_json()["request"]["photo"] == "data:image/png;base64,AAAA"
    assert ChangeRequest.query.one().payload.get("imagePhoto") is None


def test_removing_an_admin_keeps_their_requests_as_history(client, make_admin, admin_login):
    head, dist, d = setup(make_admin, admin_login)
    client.post("/api/products", headers=dist, json=NEW_PRODUCT)
    r = client.delete(f"/api/admin/auth/accounts/{d.id}", headers=head, json={"confirmPassword": PASSWORD})
    assert r.status_code == 200
    row = ChangeRequest.query.one()
    assert row.requested_by is None and row.requester_name == "Admin"
