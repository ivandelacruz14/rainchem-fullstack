import pytest

from app.models import User
from app.services import ratelimit
from conftest import PASSWORD


@pytest.fixture(autouse=True)
def fresh_limits():
    ratelimit.reset()
    yield
    ratelimit.reset()


def body(**extra):
    base = {"firstName": "Juan", "middleName": "Dela Cruz", "lastName": "Santos", "email": "juan@gmail.com",
            "phone": "09171234567", "password": PASSWORD}
    base.update(extra)
    return base


def register(client, **extra):
    return client.post("/api/auth/register", json=body(**extra))


def test_the_approved_providers_can_register(client, make_user):
    make_user()
    for email in ("juan@gmail.com", "juan.santos@yahoo.com", "juan@outlook.com", "juan@hotmail.com", "juan@ntc.edu.ph"):
        assert register(client, email=email).status_code in (200, 201), email


def test_other_domains_and_temporary_email_are_refused(client, make_user):
    make_user()
    for email in ("juan@mailinator.com", "juan@tempmail.com", "juan@10minutemail.com", "juan@guerrillamail.com", "juan@company-x.org"):
        r = register(client, email=email)
        assert r.status_code == 400, email
        assert User.query.filter_by(email=email).first() is None


def test_fake_and_placeholder_numbers_are_refused(client, make_user):
    make_user()
    for phone in ("09000000000", "09000001", "09555123456", "09111111111", "09999999999", "09123", "08123456789", "0917 123 4567"):
        r = register(client, email="fake@gmail.com", phone=phone)
        assert r.status_code == 400, phone


def test_a_real_looking_number_is_accepted(client, make_user):
    make_user()
    assert register(client, email="real@gmail.com", phone="09171234567").status_code in (200, 201)
    assert register(client, email="real2@gmail.com", phone="+639123456789").status_code in (200, 201)
    assert User.query.filter_by(email="real2@gmail.com").first().phone == "09123456789"


def test_names_are_stored_in_their_own_fields(client, make_user):
    make_user()
    register(client, email="names@gmail.com")
    u = User.query.filter_by(email="names@gmail.com").first()
    assert (u.first_name, u.middle_name, u.last_name) == ("Juan", "Dela Cruz", "Santos")
    assert u.name == "Juan Dela Cruz Santos"


def test_the_middle_name_can_be_blank(client, make_user):
    make_user()
    assert register(client, email="nomid@gmail.com", middleName="").status_code in (200, 201)
    assert User.query.filter_by(email="nomid@gmail.com").first().middle_name is None


def test_a_first_and_last_name_are_required_and_checked(client, make_user):
    make_user()
    assert register(client, email="a@gmail.com", firstName="").status_code == 400
    assert register(client, email="b@gmail.com", lastName="   ").status_code == 400
    r = register(client, email="c@gmail.com", firstName="J0hn")
    assert r.status_code == 400 and "first name" in str(r.get_json()).lower()
    assert register(client, email="d@gmail.com", lastName="x" * 61).status_code == 400
