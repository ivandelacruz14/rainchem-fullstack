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
