from app.extensions import db
from conftest import PASSWORD, days_ago

HEAD_ONLY = [("get", "/api/admin/auth/accounts"), ("get", "/api/admin/settings/payment")]


def make_account(client, head_headers, role, **extra):
    body = {"name": role, "email": f"{role.lower().replace(' ', '')}@example.com", "role": role,
            "password": PASSWORD, "confirmPassword": PASSWORD, **extra}
    r = client.post("/api/admin/auth/accounts", headers=head_headers, json=body)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["admin"]


def status(client, headers, method, url, **kw):
    return getattr(client, method)(url, headers=headers, **kw).status_code


def test_all_four_roles_are_offered(client, make_admin, admin_login):
    make_admin()
    data = client.get("/api/admin/auth/accounts", headers=admin_login("head@example.com")).get_json()
    assert data["roles"] == ["Head Admin", "Admin", "Support Staff", "Distributor"]
    assert set(data["roleInfo"]) == set(data["roles"])
    assert "manage_orders" not in data["roleInfo"]["Distributor"]["allowed"]
    assert data["roleInfo"]["Support Staff"]["preset"] == ["orders", "manage_orders", "customers", "chatbot"]


def test_admin_role_runs_the_shop_but_not_accounts_or_payment_settings(client, make_admin, admin_login, make_product):
    make_admin()
    head = admin_login("head@example.com")
    account = make_account(client, head, "Admin")
    assert account["isHead"] is False and account["isScoped"] is False
    assert set(account["permissions"]) == {"products", "services", "orders", "manage_orders", "customers", "chatbot", "analytics"}
    h = admin_login("admin@example.com")
    someone_elses = make_product("HQ item")
    # Not limited to own products, but still goes through approval like every non-head change.
    assert status(client, h, "put", f"/api/products/{someone_elses.id}", json={"price": 99}) == 202
    assert status(client, h, "get", "/api/admin/users") == 200
    assert status(client, h, "get", "/api/admin/knowledge") == 200
    assert status(client, h, "get", "/api/admin/analytics/report") == 200
    assert status(client, h, "get", "/api/admin/orders") == 200
    for method, url in HEAD_ONLY:
        assert status(client, h, method, url) == 403, url
    assert status(client, h, "post", "/api/admin/auth/accounts", json={}) == 403


def test_support_staff_handles_orders_customers_and_chatbot_only(client, make_admin, admin_login, make_user, make_product, make_order):
    make_admin()
    account = make_account(client, admin_login("head@example.com"), "Support Staff")
    assert account["permissions"] == ["orders", "manage_orders", "customers", "chatbot"]
    h = admin_login("supportstaff@example.com")
    user = make_user()
    order = make_order(user, [(make_product(), 100, 1)], status="pending_confirmation", payment_status="unpaid")
    assert status(client, h, "get", f"/api/admin/orders/{order.id}") == 200
    full = client.get("/api/admin/orders", headers=h).get_json()
    assert full["scope"] == "full" and full["orders"][0]["customer"]["phone"]
    assert status(client, h, "get", "/api/admin/users") == 200
    assert status(client, h, "get", "/api/admin/knowledge") == 200
    for method, url in [("get", "/api/products/manage"), ("get", "/api/admin/analytics/report"), ("get", "/api/admin/services"),
                        ("get", "/api/admin/sales")] + HEAD_ONLY:
        assert status(client, h, method, url) == 403, url


def test_orders_view_without_manage_orders_is_read_only_and_private(client, make_admin, admin_login, make_user, make_product, make_order):
    make_admin()
    head = admin_login("head@example.com")
    make_account(client, head, "Support Staff", permissions=["orders"])
    h = admin_login("supportstaff@example.com")
    user = make_user()
    order = make_order(user, [(make_product(), 100, 1)])
    body = client.get("/api/admin/orders", headers=h).get_json()
    assert body["scope"] == "limited" and "09171234567" not in str(body) and "customer@example.com" not in str(body)
    assert status(client, h, "get", f"/api/admin/orders/{order.id}") == 403
    assert status(client, h, "post", f"/api/admin/orders/{order.id}/confirm") == 403


def test_older_accounts_without_saved_permissions_keep_working(client, make_admin, admin_login):
    # Accounts made before roles existed have no stored permissions; they get their role's starting set.
    make_admin("staff@example.com", "Support Staff")
    make_admin("content@example.com", "Content Manager")
    make_admin("old@example.com", "Admin")
    staff, content, old = (admin_login(e) for e in ("staff@example.com", "content@example.com", "old@example.com"))
    assert status(client, staff, "get", "/api/admin/users") == 200
    assert status(client, staff, "get", "/api/products/manage") == 403
    assert status(client, content, "get", "/api/products/manage") == 200
    assert status(client, content, "get", "/api/admin/users") == 403
    assert status(client, old, "get", "/api/admin/users") == 200
    me = client.get("/api/admin/auth/me", headers=staff).get_json()["admin"]
    assert me["permissions"] == ["orders", "manage_orders", "customers", "chatbot"]


def test_distributor_can_never_hold_the_wider_permissions(client, make_admin, admin_login):
    make_admin()
    head = admin_login("head@example.com")
    account = make_account(client, head, "Distributor", permissions=["products", "manage_orders", "customers", "chatbot"])
    assert account["permissions"] == ["products"]
    # Even if the database were edited by hand, the role still caps what applies.
    from app.models import Admin
    row = db.session.get(Admin, account["id"])
    row.permissions = ["products", "manage_orders", "customers", "chatbot"]
    db.session.commit()
    h = admin_login("distributor@example.com")
    assert status(client, h, "get", "/api/admin/users") == 403
    assert status(client, h, "get", "/api/admin/knowledge") == 403


def test_changing_a_role_resets_to_that_roles_starting_permissions(client, make_admin, admin_login):
    make_admin()
    head = admin_login("head@example.com")
    account = make_account(client, head, "Distributor", permissions=["products"])
    r = client.put(f"/api/admin/auth/accounts/{account['id']}", headers=head, json={"role": "Support Staff", "confirmPassword": PASSWORD})
    assert r.get_json()["admin"]["permissions"] == ["orders", "manage_orders", "customers", "chatbot"]
    r = client.put(f"/api/admin/auth/accounts/{account['id']}", headers=head, json={"role": "Head Admin", "confirmPassword": PASSWORD})
    assert r.get_json()["admin"]["isHead"] is True
    r = client.put(f"/api/admin/auth/accounts/{account['id']}", headers=head, json={"role": "Wizard", "confirmPassword": PASSWORD})
    assert r.status_code == 400


def test_legacy_role_can_be_kept_when_editing_other_fields(client, make_admin, admin_login):
    make_admin()
    legacy = make_admin("content@example.com", "Content Manager")
    head = admin_login("head@example.com")
    r = client.put(f"/api/admin/auth/accounts/{legacy.id}", headers=head, json={"name": "Renamed", "role": "Content Manager", "confirmPassword": PASSWORD})
    assert r.status_code == 200 and r.get_json()["admin"]["role"] == "Content Manager"


def test_products_manage_lists_distributors_for_assignment(client, make_admin, admin_login):
    make_admin()
    make_admin("d@example.com", "Distributor", ["products"])
    make_admin("a@example.com", "Admin")
    data = client.get("/api/products/manage", headers=admin_login("a@example.com")).get_json()
    assert [d["name"] for d in data["distributors"]] == ["Admin"]  # make_admin names every account "Admin"
    assert "distributors" not in client.get("/api/products/manage", headers=admin_login("d@example.com")).get_json()
