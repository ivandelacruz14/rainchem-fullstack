import pytest

from app.extensions import db
from app.models import EmailVerification, User
from app.services import ratelimit
from app.services.auth_utils import normalize_ph_mobile
from conftest import PASSWORD


@pytest.fixture(autouse=True)
def fresh_limits():
    ratelimit.reset()
    yield
    ratelimit.reset()


def register(client, email="new@example.com", phone="09171234567"):
    return client.post("/api/auth/register", json={"name": "New Person", "email": email, "phone": phone, "password": PASSWORD})


@pytest.mark.parametrize("raw, expected", [
    ("09123456789", "09123456789"),
    ("+639123456789", "09123456789"),
    ("0912345678", None),
    ("091234567890", None),
    ("08123456789", None),
    ("0912 345 6789", None),
    ("0912-345-6789", None),
    ("+63912345678", None),
    ("0912345678a", None),
    ("", None),
])
def test_only_philippine_mobile_numbers_are_accepted(raw, expected):
    assert normalize_ph_mobile(raw) == expected


def test_a_plus_63_number_is_saved_in_the_local_format(client, make_user):
    make_user()
    r = register(client, email="plus@example.com", phone="+639171234567")
    assert r.status_code in (200, 201)
    assert User.query.filter_by(email="plus@example.com").first().phone == "09171234567"


def test_a_bad_phone_number_is_refused(client, make_user):
    make_user()
    r = register(client, email="bad@example.com", phone="0917123456")
    assert r.status_code == 400 and User.query.filter_by(email="bad@example.com").first() is None


def test_a_disposable_email_is_refused(client, make_user):
    make_user()
    r = register(client, email="someone@mailinator.com")
    assert r.status_code == 400 and "Temporary email" in str(r.get_json())
    assert User.query.filter_by(email="someone@mailinator.com").first() is None


def test_a_wrong_code_is_counted_and_five_wrong_tries_lock_the_code(client, make_user):
    import datetime
    user = make_user()
    user.verified = False
    db.session.commit()
    EmailVerification.query.filter_by(user_id=user.id).delete()
    db.session.add(EmailVerification(user_id=user.id, code="654321", attempts=0, created_at=datetime.datetime.utcnow(),
                                     expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=10)))
    db.session.commit()
    for _ in range(4):
        assert client.post("/api/auth/verify-email", json={"email": "customer@example.com", "code": "000000"}).status_code == 400
    r = client.post("/api/auth/verify-email", json={"email": "customer@example.com", "code": "000000"})
    assert r.status_code == 400 and "Too many wrong attempts" in r.get_json()["error"]   # the fifth wrong try uses up the code
    assert client.post("/api/auth/verify-email", json={"email": "customer@example.com", "code": "000000"}).status_code == 429
    assert client.post("/api/auth/verify-email", json={"email": "customer@example.com", "code": "654321"}).status_code == 429
    assert User.query.filter_by(email="customer@example.com").first().verified is False


def test_the_right_code_verifies_the_email(client, make_user):
    import datetime
    user = make_user()
    user.verified = False
    db.session.commit()
    EmailVerification.query.filter_by(user_id=user.id).delete()
    db.session.add(EmailVerification(user_id=user.id, code="246810", attempts=0, created_at=datetime.datetime.utcnow(),
                                     expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=10)))
    db.session.commit()
    r = client.post("/api/auth/verify-email", json={"email": "customer@example.com", "code": "246810"})
    assert r.status_code == 200 and User.query.filter_by(email="customer@example.com").first().verified is True


def test_a_new_code_cannot_be_requested_within_the_cooldown(client, make_user):
    make_user()
    h = {"Content-Type": "application/json"}
    assert client.post("/api/auth/resend-code", json={"email": "customer@example.com"}).status_code == 200
    r = client.post("/api/auth/resend-code", json={"email": "customer@example.com"})
    assert r.status_code == 429 and "Please wait" in r.get_json()["error"]


def test_daily_code_requests_are_capped(app, client, make_user):
    user = make_user()
    import datetime
    app.config["OTP_RESEND_COOLDOWN_SECONDS"] = 0
    try:
        for _ in range(app.config["OTP_MAX_PER_DAY"]):
            assert client.post("/api/auth/resend-code", json={"email": "customer@example.com"}).status_code == 200
        r = client.post("/api/auth/resend-code", json={"email": "customer@example.com"})
        assert r.status_code == 429 and "tomorrow" in r.get_json()["error"]
    finally:
        app.config["OTP_RESEND_COOLDOWN_SECONDS"] = 60


def test_registrations_from_one_connection_are_limited(app, client, make_user):
    make_user()
    app.config["REGISTER_LIMIT_PER_HOUR"] = 2
    try:
        assert register(client, email="a1@example.com").status_code in (200, 201)
        assert register(client, email="a2@example.com").status_code in (200, 201)
        r = register(client, email="a3@example.com")
        assert r.status_code == 429
    finally:
        app.config["REGISTER_LIMIT_PER_HOUR"] = 20
