from app.extensions import db
from app.models import AuditLog, User
from conftest import PASSWORD


def business_user(email="customer@example.com", verified=False):
    user = User.query.filter_by(email=email).first()
    user.account_type, user.business_name, user.business_verified = "business", "Juan Hardware", verified
    db.session.commit()
    return user


def test_admin_verifies_a_business_and_it_is_audited(client, make_user, make_admin, admin_login):
    make_user()
    user = business_user()
    make_admin()
    h = admin_login("head@example.com")
    r = client.put(f"/api/admin/users/{user.id}/business", headers=h, json={"businessVerified": True, "reason": "BIR certificate checked"})
    assert r.status_code == 200 and r.get_json()["user"]["businessVerified"] is True
    entry = AuditLog.query.filter_by(action="business_verification").one()
    assert entry.old_value == {"verified": False} and entry.new_value == {"verified": True} and entry.reason


def test_a_personal_account_cannot_be_verified(client, make_user, make_admin, admin_login):
    user = make_user()
    make_admin()
    r = client.put(f"/api/admin/users/{user.id}/business", headers=admin_login("head@example.com"), json={"businessVerified": True})
    assert r.status_code == 400


def test_a_support_staff_without_customers_permission_cannot_verify(client, make_user, make_admin, admin_login):
    make_user()
    business_user()
    user = User.query.filter_by(email="customer@example.com").first()
    make_admin("staff@example.com", "Support Staff", ["orders"])
    r = client.put(f"/api/admin/users/{user.id}/business", headers=admin_login("staff@example.com"), json={"businessVerified": True})
    assert r.status_code == 403


def test_the_profile_carries_the_account_type(client, make_user, user_login):
    make_user()
    business_user(verified=True)
    me = client.get("/api/auth/me", headers=user_login("customer@example.com")).get_json()["user"]
    assert me["accountType"] == "business" and me["businessName"] == "Juan Hardware" and me["businessVerified"] is True
