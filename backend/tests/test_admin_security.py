import re
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import AdminLoginChallenge, AdminSession
from conftest import PASSWORD, auth


@pytest.fixture()
def otp_on(app, monkeypatch):
    """Turns on the emailed code and captures the emails instead of sending them."""
    app.config["ADMIN_OTP_REQUIRED"] = True
    sent = []
    monkeypatch.setattr("app.services.admin_login_otp.send_email", lambda to, subject, body, **kw: sent.append((to, body, kw)) or True)
    yield sent
    app.config["ADMIN_OTP_REQUIRED"] = False


def code_from(sent):
    for to, body, kw in reversed(sent):
        found = re.search(r"login code is (\d{6})", body)
        if found:
            return found.group(1)
    raise AssertionError("no login code was emailed")


def password_step(client, email="head@example.com"):
    return client.post("/api/admin/auth/login", json={"email": email, "password": PASSWORD})


def finish_login(client, otp_on, email="head@example.com"):
    r = password_step(client, email)
    assert r.status_code == 202, r.get_json()
    r = client.post("/api/admin/auth/login/verify", json={"challenge": r.get_json()["challenge"], "code": code_from(otp_on)})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["token"]


def session_of(token):
    from flask_jwt_extended import decode_token
    return db.session.get(AdminSession, decode_token(token)["sid"])


def ago(minutes):
    return datetime.utcnow() - timedelta(minutes=minutes)


# ---------------------------------------------------------------- the emailed code

def test_password_alone_does_not_sign_in_when_the_code_is_on(client, make_admin, otp_on):
    make_admin()
    r = password_step(client)
    assert r.status_code == 202
    body = r.get_json()
    assert body["otpRequired"] is True and "token" not in body
    assert "*" in body["maskedEmail"] and body["maskedEmail"].endswith("@example.com")
    assert len(otp_on) == 1 and otp_on[0][0] == "head@example.com"          # the code goes to the admin's own address
    assert otp_on[0][2]["sensitive"] is True
    assert AdminSession.query.count() == 0                                   # no session until the code is right


def test_the_right_code_signs_in_and_opens_a_session(client, make_admin, otp_on):
    make_admin()
    token = finish_login(client, otp_on)
    me = client.get("/api/admin/auth/me", headers=auth(token)).get_json()
    assert me["admin"]["email"] == "head@example.com" and me["idleMinutes"] == 10
    assert session_of(token).ended_at is None


def test_wrong_password_sends_no_code(client, make_admin, otp_on):
    make_admin()
    assert client.post("/api/admin/auth/login", json={"email": "head@example.com", "password": "nope"}).status_code == 401
    assert otp_on == []


def test_a_code_works_once_and_five_wrong_tries_lock_the_attempt(client, make_admin, otp_on):
    make_admin()
    challenge = password_step(client).get_json()["challenge"]
    right = code_from(otp_on)
    wrong = "000000" if right != "000000" else "111111"
    first = client.post("/api/admin/auth/login/verify", json={"challenge": challenge, "code": wrong})
    assert first.status_code == 400 and "4 na tries" in first.get_json()["error"]
    for _ in range(4):
        client.post("/api/admin/auth/login/verify", json={"challenge": challenge, "code": wrong})
    assert client.post("/api/admin/auth/login/verify", json={"challenge": challenge, "code": right}).status_code == 429
    again = password_step(client)                                                     # a fresh attempt needs the cooldown to pass
    assert again.status_code == 429
    AdminLoginChallenge.query.update({"created_at": ago(5)})
    db.session.commit()
    challenge2 = password_step(client).get_json()["challenge"]
    good = code_from(otp_on)
    assert client.post("/api/admin/auth/login/verify", json={"challenge": challenge2, "code": good}).status_code == 200
    assert client.post("/api/admin/auth/login/verify", json={"challenge": challenge2, "code": good}).status_code == 400   # used


def test_an_expired_code_is_refused(client, make_admin, otp_on):
    make_admin()
    challenge = password_step(client).get_json()["challenge"]
    AdminLoginChallenge.query.update({"expires_at": datetime.utcnow() - timedelta(seconds=1)})
    db.session.commit()
    r = client.post("/api/admin/auth/login/verify", json={"challenge": challenge, "code": code_from(otp_on)})
    assert r.status_code == 400 and "Nag-expire" in r.get_json()["error"]


def test_a_second_password_step_within_the_cooldown_is_refused(client, make_admin, otp_on):
    make_admin()
    assert password_step(client).status_code == 202
    r = password_step(client)
    assert r.status_code == 429 and len(otp_on) == 1


def test_an_unknown_challenge_cannot_be_used(client, make_admin, otp_on):
    make_admin()
    password_step(client)
    r = client.post("/api/admin/auth/login/verify", json={"challenge": "made-up", "code": code_from(otp_on)})
    assert r.status_code == 400


def test_the_code_is_only_stored_as_a_hash(client, make_admin, otp_on):
    make_admin()
    password_step(client)
    row = AdminLoginChallenge.query.one()
    code = code_from(otp_on)
    assert code not in (row.code_hash, row.salt) and len(row.code_hash) == 64 and len(row.challenge_hash) == 64


def test_no_working_code_is_left_when_the_email_cannot_be_sent(app, client, make_admin, monkeypatch):
    app.config["ADMIN_OTP_REQUIRED"] = True
    make_admin()
    monkeypatch.setattr("app.services.admin_login_otp.send_email", lambda *a, **k: False)
    try:
        r = password_step(client)
        assert r.status_code == 503 and AdminLoginChallenge.query.filter_by(used=False).count() == 0
    finally:
        app.config["ADMIN_OTP_REQUIRED"] = False


def test_a_disabled_admin_cannot_finish_a_login(client, make_admin, otp_on):
    admin = make_admin()
    challenge = password_step(client).get_json()["challenge"]
    admin.is_active = False
    db.session.commit()
    r = client.post("/api/admin/auth/login/verify", json={"challenge": challenge, "code": code_from(otp_on)})
    assert r.status_code == 403 and AdminSession.query.count() == 0


# ---------------------------------------------------------------- idle timeout and session limits

def test_idle_for_longer_than_the_limit_signs_the_admin_out(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    assert client.get("/api/admin/auth/me", headers=h).status_code == 200
    session = AdminSession.query.one()
    session.last_seen_at = ago(11)
    db.session.commit()
    r = client.get("/api/admin/auth/me", headers=h)
    assert r.status_code == 401 and r.get_json()["reason"] == "idle"
    assert "10 minuto" in r.get_json()["error"]
    assert client.get("/api/admin/auth/me", headers=h).get_json()["reason"] == "idle"     # stays signed out


def test_activity_within_the_limit_keeps_the_session_alive(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    session = AdminSession.query.one()
    session.last_seen_at = ago(9)
    db.session.commit()
    assert client.get("/api/admin/auth/me", headers=h).status_code == 200
    assert AdminSession.query.one().ended_at is None


def test_heartbeat_keeps_a_reader_signed_in_and_reports_the_limit(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    AdminSession.query.update({"last_seen_at": ago(9)})
    db.session.commit()
    r = client.post("/api/admin/auth/heartbeat", headers=h)
    assert r.status_code == 200 and r.get_json() == {"ok": True, "idleMinutes": 10}
    AdminSession.query.update({"last_seen_at": ago(9)})
    db.session.commit()
    assert client.get("/api/admin/auth/me", headers=h).status_code == 200


def test_the_session_ends_after_the_absolute_limit_even_if_active(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    AdminSession.query.update({"expires_at": datetime.utcnow() - timedelta(minutes=1), "last_seen_at": datetime.utcnow()})
    db.session.commit()
    r = client.get("/api/admin/auth/me", headers=h)
    assert r.status_code == 401 and r.get_json()["reason"] == "expired"


def test_logout_ends_the_session_on_the_server(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    assert client.post("/api/admin/auth/logout", headers=h).status_code == 200
    assert client.get("/api/admin/auth/me", headers=h).get_json()["reason"] == "logout"
    assert client.post("/api/admin/auth/logout", headers=h).status_code == 200          # harmless the second time


def test_logout_with_an_expired_token_still_answers(client):
    assert client.post("/api/admin/auth/logout", headers={"Authorization": "Bearer not-a-token"}).status_code == 200


def test_a_token_without_a_session_is_refused(client, make_admin, admin_login):
    from flask_jwt_extended import create_access_token
    admin = make_admin()
    old = create_access_token(identity=f"admin:{admin.id}", additional_claims={"role": "admin"})
    r = client.get("/api/admin/auth/me", headers=auth(old))
    assert r.status_code == 401 and r.get_json()["reason"] == "ended"


def test_a_session_cannot_be_used_by_another_admin(client, make_admin, admin_login):
    from flask_jwt_extended import create_access_token
    first = make_admin("first@example.com", "Head Admin")
    second = make_admin("second@example.com", "Head Admin")
    h = admin_login("first@example.com")
    sid = AdminSession.query.one().id
    stolen = create_access_token(identity=f"admin:{second.id}", additional_claims={"role": "admin", "sid": sid})
    assert client.get("/api/admin/auth/me", headers=auth(stolen)).status_code == 401


def test_customers_stay_out_of_admin_pages_regardless(client, make_user, user_login, make_admin, otp_on):
    make_user()
    make_admin()
    assert client.get("/api/admin/auth/me", headers=user_login("customer@example.com")).status_code == 403
    assert client.post("/api/admin/auth/heartbeat", headers=user_login("customer@example.com")).status_code == 403


def test_the_limits_come_from_configuration(app, client, make_admin, admin_login):
    make_admin()
    app.config["ADMIN_IDLE_MINUTES"] = 5
    h = admin_login("head@example.com")
    AdminSession.query.update({"last_seen_at": ago(6)})
    db.session.commit()
    r = client.get("/api/admin/auth/me", headers=h)
    assert r.status_code == 401 and "5 minuto" in r.get_json()["error"]
    app.config["ADMIN_IDLE_MINUTES"] = 10
