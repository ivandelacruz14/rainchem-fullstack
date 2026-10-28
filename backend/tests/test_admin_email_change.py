import re
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Admin, AdminEmailChange
from conftest import PASSWORD, auth


@pytest.fixture()
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr("app.services.admin_email_change.send_email", lambda to, subject, body, **kw: sent.append((to, subject, body, kw)) or True)
    return sent


def code_of(outbox):
    for to, subject, body, kw in reversed(outbox):
        found = re.search(r"confirmation code is (\d{6})", body)
        if found:
            return found.group(1)
    raise AssertionError("no code sent")


def start(client, h, email="new@example.com", password=PASSWORD):
    return client.post("/api/admin/auth/me/email/start", headers=h, json={"password": password, "newEmail": email})


def confirm(client, h, code):
    return client.post("/api/admin/auth/me/email/confirm", headers=h, json={"code": code})


def test_email_changes_only_after_the_code_from_the_new_address(client, make_admin, admin_login, outbox):
    make_admin("wrong@example.com", "Head Admin")
    h = admin_login("wrong@example.com")
    assert start(client, h, "Right@Example.com").status_code == 200
    to, subject, body, kw = outbox[0]
    assert to == "right@example.com" and kw["sensitive"] is True          # the code goes to the NEW address
    assert db.session.query(Admin).one().email == "wrong@example.com"     # nothing changed yet

    r = confirm(client, h, code_of(outbox))
    assert r.status_code == 200 and r.get_json()["admin"]["email"] == "right@example.com"
    assert client.post("/api/admin/auth/login", json={"email": "right@example.com", "password": PASSWORD}).status_code == 200
    assert client.post("/api/admin/auth/login", json={"email": "wrong@example.com", "password": PASSWORD}).status_code == 401
    assert outbox[-1][0] == "wrong@example.com" and "changed" in outbox[-1][1]   # old address is told


def test_password_and_address_are_checked(client, make_admin, admin_login, outbox):
    make_admin("a@example.com", "Head Admin")
    make_admin("b@example.com", "Support Staff")
    h = admin_login("a@example.com")
    assert start(client, h, password="wrong").status_code == 403
    assert start(client, h, email="not-an-email").status_code == 400
    assert start(client, h, email="a@example.com").status_code == 400
    assert start(client, h, email="B@example.com").status_code == 400      # used by another admin
    assert outbox == []


def test_wrong_code_expired_code_and_reuse(client, make_admin, admin_login, outbox):
    make_admin("a@example.com", "Head Admin")
    h = admin_login("a@example.com")
    assert confirm(client, h, "123456").status_code == 400                # nothing was requested
    start(client, h)
    code = code_of(outbox)
    wrong = "000000" if code != "000000" else "111111"
    r = confirm(client, h, wrong)
    assert r.status_code == 400 and "4 tries left" in r.get_json()["error"]
    for _ in range(4):
        confirm(client, h, wrong)
    assert confirm(client, h, code).status_code == 429                    # locked after 5 wrong tries
    assert db.session.query(Admin).one().email == "a@example.com"

    AdminEmailChange.query.update({"created_at": datetime.utcnow() - timedelta(minutes=5)})
    db.session.commit()
    start(client, h)
    AdminEmailChange.query.filter_by(used=False).update({"expires_at": datetime.utcnow() - timedelta(seconds=1)})
    db.session.commit()
    assert "expired" in confirm(client, h, code_of(outbox)).get_json()["error"]

    AdminEmailChange.query.update({"created_at": datetime.utcnow() - timedelta(minutes=5)})
    db.session.commit()
    start(client, h)
    good = code_of(outbox)
    assert confirm(client, h, good).status_code == 200
    assert confirm(client, h, good).status_code == 400                    # a used code does nothing


def test_code_is_hashed_and_requests_are_slowed(client, make_admin, admin_login, outbox):
    make_admin("a@example.com", "Head Admin")
    h = admin_login("a@example.com")
    start(client, h)
    row = AdminEmailChange.query.one()
    assert code_of(outbox) not in (row.code_hash, row.salt)
    assert start(client, h).status_code == 429


def test_email_cannot_be_changed_when_the_mail_cannot_be_sent(client, make_admin, admin_login, monkeypatch):
    make_admin("a@example.com", "Head Admin")
    h = admin_login("a@example.com")
    monkeypatch.setattr("app.services.admin_email_change.send_email", lambda *a, **k: False)
    r = start(client, h)
    assert r.status_code == 503 and AdminEmailChange.query.filter_by(used=False).count() == 0


def test_only_your_own_email_and_only_when_signed_in(client, make_admin, admin_login, make_user, user_login, outbox):
    make_admin("a@example.com", "Head Admin")
    assert client.post("/api/admin/auth/me/email/start", json={}).status_code == 401
    make_user()
    assert client.post("/api/admin/auth/me/email/start", headers=user_login("customer@example.com"), json={}).status_code == 403
    d = make_admin("d@example.com", "Distributor", ["products"])
    dh = admin_login("d@example.com")
    start(client, dh, "dnew@example.com")
    confirm(client, dh, code_of(outbox))
    assert db.session.get(Admin, d.id).email == "dnew@example.com"
    assert db.session.query(Admin).filter_by(email="a@example.com").count() == 1   # the head's email is untouched


def test_changed_email_receives_approval_codes(client, make_admin, admin_login, outbox, mailbox, make_product):
    from conftest import emailed_code
    make_admin("wrong@example.com", "Head Admin")
    make_admin("d@example.com", "Distributor", ["products"])
    head, dist = admin_login("wrong@example.com"), admin_login("d@example.com")
    start(client, head, "right@example.com")
    confirm(client, head, code_of(outbox))
    rid = client.post("/api/products", headers=dist, json={"name": "X", "category": "Coolant", "price": 5, "stock": 1, "shortDesc": "s", "description": "d"}).get_json()["request"]["id"]
    mailbox.clear()
    client.post(f"/api/admin/approvals/{rid}/approve/start", headers=head, json={"password": PASSWORD})
    assert mailbox[0]["to"] == "right@example.com" and emailed_code(mailbox)
