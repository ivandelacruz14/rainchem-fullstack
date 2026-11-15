import pytest
import requests

from conftest import PASSWORD


class FakeResponse:
    def __init__(self, body, ok=True):
        self._body, self.ok = body, ok

    def json(self):
        return self._body


@pytest.fixture()
def captcha_on(app):
    app.config["TURNSTILE_SECRET_KEY"] = "test-secret"
    yield
    app.config["TURNSTILE_SECRET_KEY"] = ""


def cloudflare(monkeypatch, body=None, ok=True, error=None):
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append({"url": url, "data": data})
        if error is not None:
            raise error
        return FakeResponse(body if body is not None else {"success": True}, ok)

    monkeypatch.setattr("app.services.captcha.requests.post", fake_post)
    return calls


def login(client, email="customer@example.com", token=None):
    body = {"email": email, "password": PASSWORD}
    if token is not None:
        body["captchaToken"] = token
    return client.post("/api/auth/login", json=body)


def test_nothing_is_checked_when_no_secret_key_is_set(client, make_user, monkeypatch):
    calls = cloudflare(monkeypatch)
    make_user()
    assert login(client).status_code == 200
    assert calls == []


def test_login_without_a_check_is_refused(client, make_user, captcha_on, monkeypatch):
    calls = cloudflare(monkeypatch)
    make_user()
    r = login(client)
    assert r.status_code == 400 and "security check" in r.get_json()["error"]
    assert calls == []


def test_a_passed_check_lets_the_login_through(client, make_user, captcha_on, monkeypatch):
    calls = cloudflare(monkeypatch)
    make_user()
    assert login(client, token="good-token").status_code == 200
    assert calls[0]["url"].endswith("/turnstile/v0/siteverify")
    assert calls[0]["data"]["response"] == "good-token" and calls[0]["data"]["secret"] == "test-secret"


def test_a_failed_check_is_refused(client, make_user, captcha_on, monkeypatch):
    cloudflare(monkeypatch, body={"success": False, "error-codes": ["invalid-input-response"]})
    make_user()
    r = login(client, token="bad-token")
    assert r.status_code == 400 and "failed" in r.get_json()["error"]


def test_an_unreachable_check_service_fails_closed(client, make_user, captcha_on, monkeypatch):
    cloudflare(monkeypatch, error=requests.ConnectionError("down"))
    make_user()
    r = login(client, token="any")
    assert r.status_code == 503


def test_register_and_forgot_password_are_protected(client, make_user, captcha_on, monkeypatch):
    calls = cloudflare(monkeypatch)
    make_user()
    assert client.post("/api/auth/register", json={"name": "New", "email": "new@example.com", "password": PASSWORD}).status_code == 400
    assert client.post("/api/auth/forgot-password", json={"email": "customer@example.com"}).status_code == 400
    assert calls == []
    assert client.post("/api/auth/forgot-password", json={"email": "customer@example.com", "captchaToken": "ok"}).status_code == 200
    assert len(calls) == 1


def test_admin_sign_in_is_protected(client, make_admin, captcha_on, monkeypatch):
    calls = cloudflare(monkeypatch)
    make_admin()
    body = {"email": "head@example.com", "password": PASSWORD}
    assert client.post("/api/admin/auth/login", json=body).status_code == 400
    assert calls == []
    assert client.post("/api/admin/auth/login", json={**body, "captchaToken": "ok"}).status_code == 200
