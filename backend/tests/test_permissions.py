from conftest import PASSWORD, auth


def head(make_admin, admin_login):
    make_admin("head@example.com", "Head Admin")
    return admin_login("head@example.com")


def test_limited_admin_is_refused_head_only_endpoints(client, make_admin, admin_login):
    make_admin("d@example.com", "Admin", ["products", "services", "orders", "analytics"])
    h = admin_login("d@example.com")
    for method, url in [
        ("get", "/api/admin/users"), ("get", "/api/admin/auth/accounts"), ("get", "/api/admin/settings/payment"),
        ("get", "/api/admin/knowledge"), ("get", "/api/admin/chat-monitor"), ("post", "/api/admin/orders/1/confirm"),
        ("get", "/api/admin/orders/1"),
    ]:
        assert getattr(client, method)(url, headers=h).status_code == 403, url
    assert client.post("/api/admin/auth/accounts", headers=h, json={}).status_code == 403


def test_no_token_no_access_and_customer_token_is_not_admin(client, make_user, user_login):
    assert client.get("/api/admin/overview").status_code == 401
    make_user()
    assert client.get("/api/admin/users", headers=user_login("customer@example.com")).status_code == 403


def test_missing_permission_blocks_even_with_valid_login(client, make_admin, admin_login):
    make_admin("d@example.com", "Admin", ["orders"])
    h = admin_login("d@example.com")
    assert client.post("/api/products", headers=h, json={"name": "x"}).status_code == 403
    assert client.get("/api/admin/analytics/report", headers=h).status_code == 403
    assert client.get("/api/admin/services", headers=h).status_code == 403
    assert client.get("/api/admin/orders", headers=h).status_code == 200


def test_non_head_product_changes_are_requests_for_any_product(client, make_admin, admin_login, make_product, approve):
    from app.models import Product
    make_admin("head@example.com", "Head Admin")
    make_admin("a1@example.com", "Admin", ["products"])
    one, two = make_product("One"), make_product("Two")
    h = admin_login("a1@example.com")

    # Every product is listed; there are no owners or per-account limits any more.
    listing = client.get("/api/products/manage", headers=h).get_json()
    assert sorted(p["name"] for p in listing["products"]) == ["One", "Two"]
    assert "distributors" not in listing and all("ownerId" not in p for p in listing["products"])

    # Changes by a non-head admin are requests until the Head Admin approves them.
    assert client.put(f"/api/products/{two.id}", headers=h, json={"price": 99}).status_code == 202
    assert float(db_price(Product, two.id)) == 500

    body = {"name": "New", "category": "Coolant", "price": 10, "stock": 5, "shortDesc": "s", "description": "d"}
    created = client.post("/api/products", headers=h, json=body)
    assert created.status_code == 202
    head_h = admin_login("head@example.com")
    assert approve(head_h, created.get_json()["request"]["id"]).status_code == 200
    assert Product.query.filter_by(name="New").count() == 1


def db_price(model, product_id):
    from app.extensions import db
    return db.session.get(model, product_id).price


def test_product_input_is_validated(client, make_admin, admin_login):
    h = head(make_admin, admin_login)
    bad = client.post("/api/products", headers=h, json={"name": "", "price": -5, "stock": "x", "category": "Nope"})
    assert bad.status_code == 400


def test_disabled_admin_token_stops_working(client, make_admin, admin_login):
    admin = make_admin("d@example.com", "Admin", ["products"])
    h = admin_login("d@example.com")
    assert client.get("/api/products/manage", headers=h).status_code == 200
    admin.is_active = False
    from app.extensions import db
    db.session.commit()
    assert client.get("/api/products/manage", headers=h).status_code == 401
    assert client.post("/api/admin/auth/login", json={"email": "d@example.com", "password": PASSWORD}).status_code == 403


def test_legacy_admin_roles_keep_full_access(client, make_admin, admin_login):
    make_admin("old@example.com", "Super Admin")
    make_admin("old2@example.com", "Admin")
    for email in ("old@example.com", "old2@example.com"):
        assert client.get("/api/admin/users", headers=admin_login(email)).status_code == 200


def test_account_management_rules(client, make_admin, admin_login):
    h = head(make_admin, admin_login)
    payload = {"name": "Dist", "email": "dist@example.com", "role": "Admin", "password": PASSWORD,
               "permissions": ["products", "bogus"]}
    assert client.post("/api/admin/auth/accounts", headers=h, json=payload).status_code == 403  # no confirmation
    created = client.post("/api/admin/auth/accounts", headers=h, json={**payload, "confirmPassword": "wrong"})
    assert created.status_code == 403
    created = client.post("/api/admin/auth/accounts", headers=h, json={**payload, "confirmPassword": PASSWORD})
    assert created.status_code == 201
    account = created.get_json()["admin"]
    assert account["permissions"] == ["products"] and account["isHead"] is False

    weak = client.post("/api/admin/auth/accounts", headers=h, json={**payload, "email": "x@example.com", "password": "abc", "confirmPassword": PASSWORD})
    assert weak.status_code == 400
    dup = client.post("/api/admin/auth/accounts", headers=h, json={**payload, "confirmPassword": PASSWORD})
    assert dup.status_code == 400

    upd = client.put(f"/api/admin/auth/accounts/{account['id']}", headers=h,
                     json={"permissions": ["services", "orders"], "confirmPassword": PASSWORD})
    assert upd.get_json()["admin"]["permissions"] == ["services", "orders"]

    me = client.get("/api/admin/auth/me", headers=h).get_json()["admin"]
    own = client.put(f"/api/admin/auth/accounts/{me['id']}", headers=h, json={"role": "Admin", "confirmPassword": PASSWORD})
    assert own.status_code == 400
    assert client.delete(f"/api/admin/auth/accounts/{me['id']}", headers=h, json={"confirmPassword": PASSWORD}).status_code == 400

    # A limited account cannot change its own permissions.
    dh = admin_login("dist@example.com")
    assert client.put(f"/api/admin/auth/accounts/{account['id']}", headers=dh, json={"permissions": ["products"], "confirmPassword": PASSWORD}).status_code == 403

    assert client.delete(f"/api/admin/auth/accounts/{account['id']}", headers=h, json={"confirmPassword": PASSWORD}).status_code == 200


def test_last_head_admin_cannot_be_demoted_or_removed(client, make_admin, admin_login):
    h = head(make_admin, admin_login)
    other = make_admin("h2@example.com", "Head Admin")
    # Removing the other head is fine because the caller remains.
    assert client.put(f"/api/admin/auth/accounts/{other.id}", headers=h, json={"isActive": False, "confirmPassword": PASSWORD}).status_code == 200
    third = make_admin("h3@example.com", "Admin")
    assert client.put(f"/api/admin/auth/accounts/{third.id}", headers=h, json={"role": "Head Admin", "confirmPassword": PASSWORD}).status_code == 200


def test_there_is_no_public_admin_signup(client):
    assert client.post("/api/admin/auth/accounts", json={"email": "a@b.co"}).status_code == 401
    assert client.post("/api/admin/auth/register", json={}).status_code == 404
