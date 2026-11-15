import pytest
import requests

from app.services import email_service


class Reply:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = ""


@pytest.fixture()
def mail(app, monkeypatch):
    monkeypatch.setenv("MAILJET_API_KEY", "key")
    monkeypatch.setenv("MAILJET_API_SECRET", "secret")
    app.config["SMTP_FROM"] = "no-reply@example.com"
    monkeypatch.setattr("app.services.email_service.time.sleep", lambda s: None)


def test_a_dropped_connection_is_retried_and_the_email_is_sent(app, mail, monkeypatch):
    calls = []

    def flaky(url, **kwargs):
        calls.append(url)
        if len(calls) < 3:
            raise requests.ConnectionError("Connection reset by peer")
        return Reply(200)

    monkeypatch.setattr("app.services.email_service.requests.post", flaky)
    with app.app_context():
        assert email_service.send_email("admin@example.com", "Code", "123456") is True
    assert len(calls) == 3


def test_a_connection_that_keeps_failing_gives_up_after_three_tries(app, mail, monkeypatch):
    calls = []

    def down(url, **kwargs):
        calls.append(url)
        raise requests.ConnectionError("Connection reset by peer")

    monkeypatch.setattr("app.services.email_service.requests.post", down)
    with app.app_context():
        assert email_service.send_email("admin@example.com", "Code", "123456") is False
    assert len(calls) == 3


def test_an_error_reply_from_mailjet_is_not_retried(app, mail, monkeypatch):
    calls = []

    def rejected(url, **kwargs):
        calls.append(url)
        return Reply(401)

    monkeypatch.setattr("app.services.email_service.requests.post", rejected)
    with app.app_context():
        assert email_service.send_email("admin@example.com", "Code", "123456") is False
    assert len(calls) == 1


def test_resend_is_used_when_it_is_the_chosen_provider(app, mail, monkeypatch):
    app.config["EMAIL_PROVIDER"] = "resend"
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    calls = []

    def fake(url, **kwargs):
        calls.append((url, kwargs["headers"]["Authorization"]))
        return Reply(200)

    monkeypatch.setattr("app.services.email_service.requests.post", fake)
    try:
        with app.app_context():
            assert email_service.send_email("admin@example.com", "Code", "123456") is True
    finally:
        app.config["EMAIL_PROVIDER"] = "mailjet"
    assert calls == [("https://api.resend.com/emails", "Bearer re_test")]


def test_mailjet_connection_failure_falls_back_to_resend(app, mail, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    urls = []

    def fake(url, **kwargs):
        urls.append(url)
        if "mailjet" in url:
            raise requests.ConnectionError("Connection reset by peer")
        return Reply(200)

    monkeypatch.setattr("app.services.email_service.requests.post", fake)
    with app.app_context():
        assert email_service.send_email("admin@example.com", "Code", "123456") is True
    assert urls[-1] == "https://api.resend.com/emails"


def test_a_mailjet_error_reply_does_not_fall_back(app, mail, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    urls = []

    def fake(url, **kwargs):
        urls.append(url)
        return Reply(401)

    monkeypatch.setattr("app.services.email_service.requests.post", fake)
    with app.app_context():
        assert email_service.send_email("admin@example.com", "Code", "123456") is False
    assert urls == ["https://api.mailjet.com/v3.1/send"]
