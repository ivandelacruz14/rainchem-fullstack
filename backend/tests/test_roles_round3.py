from app.extensions import db
from app.models import Admin, AuditLog
from conftest import PASSWORD

ACCOUNTS = "/api/admin/auth/accounts"


def login(admin_login, email):
    return admin_login(email)


def test_a_rider_can_only_reach_the_delivery_permission(client, make_admin, admin_login):
    make_admin("rider@example.com", "Rider")
    h = login(admin_login, "rider@example.com")
    assert client.get("/api/products/manage", headers=h).status_code == 403
    assert client.get("/api/admin/orders", headers=h).status_code == 403
    assert client.get("/api/admin/analytics/report", headers=h).status_code == 403
    assert client.get("/api/admin/inventory/overview", headers=h).status_code == 403
    assert client.get("/api/admin/diagnostics/health", headers=h).status_code == 403
    assert client.get(ACCOUNTS, headers=h).status_code == 403
    assert client.get("/api/admin/auth/me", headers=h).status_code == 200


def test_a_developer_sees_health_but_no_customer_or_payment_data(client, make_admin, admin_login):
    make_admin("dev@example.com", "Developer")
    h = login(admin_login, "dev@example.com")
    r = client.get("/api/admin/diagnostics/health", headers=h)
    assert r.status_code == 200 and r.get_json()["database"] == "ok"
    assert "customer" not in str(r.get_json()).lower()
    assert client.get("/api/admin/orders", headers=h).status_code == 403
    assert client.get("/api/admin/live-chat/conversations", headers=h).status_code == 403
    assert client.get("/api/admin/sales-records", headers=h).status_code == 403
    assert client.get(ACCOUNTS, headers=h).status_code == 403


def test_a_head_cannot_touch_a_super_admin(client, make_admin, admin_login):
    make_admin()
    make_admin("super@example.com", "Super Admin")
    s = admin_login("super@example.com")
    h = admin_login("head@example.com")
    target = Admin.query.filter_by(email="super@example.com").first()
    assert client.delete(f"{ACCOUNTS}/{target.id}", headers=h, json={"confirmPassword": PASSWORD}).status_code == 403
    assert client.put(f"{ACCOUNTS}/{target.id}", headers=h, json={"isActive": False, "confirmPassword": PASSWORD}).status_code == 403
    assert client.post(f"{ACCOUNTS}/{target.id}/password", headers=h, json={"newPassword": "NewPassw0rd!", "confirmPassword": PASSWORD}).status_code == 403


def test_super_admin_cannot_be_deleted_or_remove_itself(client, make_admin, admin_login):
    make_admin("super@example.com", "Super Admin")
    make_admin("super2@example.com", "Super Admin")
    s = admin_login("super@example.com")
    other = Admin.query.filter_by(email="super2@example.com").first()
    assert client.delete(f"{ACCOUNTS}/{other.id}", headers=s, json={"confirmPassword": PASSWORD}).status_code == 403
    me = Admin.query.filter_by(email="super@example.com").first()
    assert client.delete(f"{ACCOUNTS}/{me.id}", headers=s, json={"confirmPassword": PASSWORD}).status_code == 400   # cannot remove yourself
    # One Super Admin can deactivate another while at least one stays active.
    assert client.put(f"{ACCOUNTS}/{other.id}", headers=s, json={"isActive": False, "confirmPassword": PASSWORD}).status_code == 200


def test_a_super_admin_can_manage_a_second_super_admin(client, make_admin, admin_login):
    make_admin("super@example.com", "Super Admin")
    make_admin("super2@example.com", "Super Admin")
    s = admin_login("super@example.com")
    other = Admin.query.filter_by(email="super2@example.com").first()
    assert client.put(f"{ACCOUNTS}/{other.id}", headers=s, json={"isActive": False, "confirmPassword": PASSWORD}).status_code == 200


def test_an_admin_cannot_manage_another_admin(client, make_admin, admin_login):
    make_admin("admin1@example.com", "Admin")
    make_admin("admin2@example.com", "Admin")
    a1 = admin_login("admin1@example.com")
    other = Admin.query.filter_by(email="admin2@example.com").first()
    assert client.put(f"{ACCOUNTS}/{other.id}", headers=a1, json={"isActive": False, "confirmPassword": PASSWORD}).status_code == 403


def test_only_a_super_admin_can_give_the_super_admin_role(client, make_admin, admin_login):
    make_admin()
    make_admin("super@example.com", "Super Admin")
    h = admin_login("head@example.com")
    body = {"name": "New", "email": "newsuper@example.com", "role": "Super Admin", "password": "Passw0rd!x", "confirmPassword": PASSWORD}
    assert client.post(ACCOUNTS, headers=h, json=body).status_code == 403
    s = admin_login("super@example.com")
    assert client.post(ACCOUNTS, headers=s, json=body).status_code == 201


def test_a_head_can_create_riders_and_developers_with_only_their_permission(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    rider = client.post(ACCOUNTS, headers=h, json={"name": "Ben", "email": "ben@example.com", "role": "Rider",
                                                   "password": "Passw0rd!x", "confirmPassword": PASSWORD,
                                                   "permissions": ["orders", "customers"]})
    assert rider.status_code == 201 and rider.get_json()["admin"]["permissions"] == ["deliveries"]
    dev = client.post(ACCOUNTS, headers=h, json={"name": "Dev", "email": "dev2@example.com", "role": "Developer",
                                                 "password": "Passw0rd!x", "confirmPassword": PASSWORD,
                                                 "permissions": ["customers", "diagnostics"]})
    assert dev.status_code == 201 and dev.get_json()["admin"]["permissions"] == ["diagnostics"]


def test_account_changes_are_audited(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    r = client.post(ACCOUNTS, headers=h, json={"name": "Ann", "email": "ann@example.com", "role": "Support Staff",
                                               "password": "Passw0rd!x", "confirmPassword": PASSWORD})
    new_id = r.get_json()["admin"]["id"]
    client.put(f"{ACCOUNTS}/{new_id}", headers=h, json={"isActive": False, "confirmPassword": PASSWORD})
    client.delete(f"{ACCOUNTS}/{new_id}", headers=h, json={"confirmPassword": PASSWORD})
    actions = [e.action for e in AuditLog.query.filter_by(entity_type="admin").all()]
    assert "admin_created" in actions and "admin_updated" in actions and "admin_removed" in actions


def test_approvals_are_for_product_and_service_staff_only(client, make_admin, admin_login):
    make_admin("rider@example.com", "Rider")
    make_admin("staff@example.com", "Support Staff")
    rider = admin_login("rider@example.com")
    staff = admin_login("staff@example.com")
    assert client.get("/api/admin/approvals", headers=rider).status_code == 403
    assert client.get("/api/admin/approvals", headers=staff).status_code == 403
