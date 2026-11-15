import re
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Notification, PasswordReset

from conftest import PASSWORD


def request_link(client, monkeypatch, email):
    sent = []
    monkeypatch.setattr("app.routes.auth.send_email", lambda *a, **k: sent.append((a, k)) or True)
    response = client.post("/api/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    if not sent:
        return None
    body = sent[-1][0][2]
    link = re.search(r"https?://\S+", body).group(0)
    return link, sent[-1][1]


def token_of(link):
    return link.split("token=")[1]


def test_link_points_at_the_frontend_route_not_localhost(app, client, make_user, monkeypatch):
    make_user()
    app.config["FRONTEND_BASE_URL"] = "https://raimol.example.app"
    link, kwargs = request_link(client, monkeypatch, "customer@example.com")
    assert link.startswith("https://raimol.example.app/reset-password?token=")
    assert "localhost" not in link
    assert kwargs.get("sensitive") is True


def test_unknown_email_gets_the_same_answer_and_sends_nothing(client, monkeypatch):
    assert request_link(client, monkeypatch, "nobody@example.com") is None


def test_token_is_stored_hashed_and_email_body_is_not_saved(app, client, make_user, monkeypatch):
    make_user()
    link, _ = request_link(client, monkeypatch, "customer@example.com")
    token = token_of(link)
    assert PasswordReset.query.filter_by(token=token).first() is None
    assert len(PasswordReset.query.one().token) == 64


def test_full_reset_flow_is_single_use(client, make_user, monkeypatch):
    make_user()
    link, _ = request_link(client, monkeypatch, "customer@example.com")
    token = token_of(link)

    assert client.get(f"/api/auth/reset-password/check?token={token}").get_json()["valid"] is True
    # Checking the link (what a mail scanner might do) must not use it up.
    assert client.get(f"/api/auth/reset-password/check?token={token}").get_json()["valid"] is True

    monkeypatch.setattr("app.routes.auth.send_email", lambda *a, **k: True)
    new_password = "NewPassw0rd!z"
    assert client.post("/api/auth/reset-password", json={"token": token, "password": new_password}).status_code == 200

    assert client.post("/api/auth/login", json={"email": "customer@example.com", "password": new_password}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "customer@example.com", "password": PASSWORD}).status_code == 401

    again = client.post("/api/auth/reset-password", json={"token": token, "password": "Another1!pass"})
    assert again.status_code == 400
    assert again.get_json()["reason"] == "used"
    assert client.get(f"/api/auth/reset-password/check?token={token}").get_json()["reason"] == "used"


def test_expired_and_invalid_tokens_have_clear_reasons(client, make_user, monkeypatch):
    make_user()
    link, _ = request_link(client, monkeypatch, "customer@example.com")
    token = token_of(link)
    row = PasswordReset.query.one()
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.session.commit()

    expired = client.post("/api/auth/reset-password", json={"token": token, "password": "NewPassw0rd!z"})
    assert expired.status_code == 400 and expired.get_json()["reason"] == "expired"

    invalid = client.post("/api/auth/reset-password", json={"token": "not-a-real-token", "password": "NewPassw0rd!z"})
    assert invalid.status_code == 400 and invalid.get_json()["reason"] == "invalid"


def test_weak_password_is_rejected_and_token_stays_usable(client, make_user, monkeypatch):
    make_user()
    link, _ = request_link(client, monkeypatch, "customer@example.com")
    token = token_of(link)
    weak = client.post("/api/auth/reset-password", json={"token": token, "password": "short"})
    assert weak.status_code == 400 and weak.get_json()["errors"]
    assert client.get(f"/api/auth/reset-password/check?token={token}").get_json()["valid"] is True


def test_a_new_request_replaces_the_older_link(client, make_user, monkeypatch):
    user = make_user()
    first, _ = request_link(client, monkeypatch, "customer@example.com")
    PasswordReset.query.update({"created_at": datetime.utcnow() - timedelta(minutes=5)})
    db.session.commit()
    second, _ = request_link(client, monkeypatch, "customer@example.com")
    assert client.get(f"/api/auth/reset-password/check?token={token_of(first)}").get_json()["reason"] == "used"
    assert client.get(f"/api/auth/reset-password/check?token={token_of(second)}").get_json()["valid"] is True


def test_repeated_requests_inside_the_cooldown_are_ignored(client, make_user, monkeypatch):
    make_user()
    assert request_link(client, monkeypatch, "customer@example.com") is not None
    assert request_link(client, monkeypatch, "customer@example.com") is None


def test_sensitive_emails_are_not_kept_in_notifications(app, client, make_user):
    make_user()
    from app.services.email_service import send_email
    with app.test_request_context():
        send_email("customer@example.com", "Reset", "https://x/reset-password?token=SECRET", sensitive=True)
    assert "SECRET" not in Notification.query.one().body
