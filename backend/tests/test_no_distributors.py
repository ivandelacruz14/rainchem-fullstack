from app.extensions import db
from app.models import Admin, Product
from conftest import PASSWORD


def test_distributor_is_no_longer_a_role_you_can_pick(client, make_admin, admin_login):
    make_admin()
    head = admin_login("head@example.com")
    data = client.get("/api/admin/auth/accounts", headers=head).get_json()
    assert data["roles"] == ["Head Admin", "Admin", "Support Staff"]
    assert "Distributor" not in data["roleInfo"]
    body = {"name": "D", "email": "d@example.com", "role": "Distributor", "password": PASSWORD, "confirmPassword": PASSWORD}
    assert client.post("/api/admin/auth/accounts", headers=head, json=body).status_code == 400


def test_old_distributor_accounts_keep_their_record_but_have_no_access_until_reassigned(client, make_admin, admin_login):
    make_admin()
    old = make_admin("old@example.com", "Distributor")
    h = admin_login("old@example.com")                 # they can still sign in
    me = client.get("/api/admin/auth/me", headers=h).get_json()["admin"]
    assert me["permissions"] == [] and me["isHead"] is False
    for url in ("/api/products/manage", "/api/admin/orders", "/api/admin/analytics/report", "/api/admin/users"):
        assert client.get(url, headers=h).status_code == 403, url
    head = admin_login("head@example.com")
    r = client.put(f"/api/admin/auth/accounts/{old.id}", headers=head, json={"role": "Support Staff", "confirmPassword": PASSWORD})
    assert r.status_code == 200 and "orders" in r.get_json()["admin"]["permissions"]
    assert client.get("/api/admin/orders", headers=admin_login("old@example.com")).status_code == 200


def test_every_admin_with_the_permission_sees_the_whole_catalog(client, make_admin, admin_login, make_product):
    make_admin("a@example.com", "Support Staff", ["products"])
    first, second = make_product("One"), make_product("Two")
    names = [p["name"] for p in client.get("/api/products/manage", headers=admin_login("a@example.com")).get_json()["products"]]
    assert names == ["One", "Two"]
    assert "distributors" not in client.get("/api/products/manage", headers=admin_login("a@example.com")).get_json()


def test_products_and_services_no_longer_expose_owners(client, make_admin, admin_login, make_product):
    make_admin()
    h = admin_login("head@example.com")
    p = make_product("One")
    assert "ownerId" not in client.get("/api/products/manage", headers=h).get_json()["products"][0]
    made = client.post("/api/admin/services", headers=h, json={"name": "S", "description": "d", "areas": [{"name": "QC", "price": 5}]}).get_json()["service"]
    assert "ownerId" not in made
    assert "distributors" not in client.get("/api/admin/services", headers=h).get_json()


def test_removing_an_account_that_once_owned_things_still_works(client, make_admin, admin_login, make_product):
    make_admin()
    gone = make_admin("gone@example.com", "Support Staff", ["products"])
    p = make_product("Owned once")
    db.session.get(Product, p.id).owner_admin_id = gone.id      # a leftover from the old Distributor module
    db.session.commit()
    r = client.delete(f"/api/admin/auth/accounts/{gone.id}", headers=admin_login("head@example.com"), json={"confirmPassword": PASSWORD})
    assert r.status_code == 200 and db.session.get(Product, p.id) is not None
