from app.extensions import db
from app.models import Admin, Order
from test_delivery_round4 import ready_order, riders


def confirmed_order(make_order, make_user, make_product):
    order, a, b = ready_order(make_order, make_user, make_product)
    order.status = "confirmed"
    db.session.commit()
    return order


def rider_id():
    return Admin.query.filter_by(email="rider@example.com").first().id


def test_sending_to_a_rider_needs_an_estimated_date(client, make_order, make_user, make_product, make_admin, admin_login):
    order = confirmed_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    url = f"/api/admin/orders/{order.id}/assign-rider"
    assert client.post(url, headers=head, json={"riderId": rider_id()}).status_code == 400
    assert client.post(url, headers=head, json={"riderId": rider_id(), "estimatedDate": "2000-01-01"}).status_code == 400
    ok = client.post(url, headers=head, json={"riderId": rider_id(), "estimatedDate": "2099-01-01"})
    assert ok.status_code == 200 and ok.get_json()["order"]["estimatedDelivery"] == "2099-01-01"


def test_a_rider_without_a_phone_number_cannot_be_assigned(client, make_order, make_user, make_product, make_admin, admin_login):
    order = confirmed_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    Admin.query.get(rider_id()).phone = None
    db.session.commit()
    r = client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head, json={"riderId": rider_id(), "estimatedDate": "2099-01-01"})
    assert r.status_code == 400 and "phone" in r.get_json()["error"].lower()


def test_the_customer_sees_the_rider_and_the_estimated_date(client, make_order, make_user, make_product, make_admin, admin_login, user_login):
    order = confirmed_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head, json={"riderId": rider_id(), "estimatedDate": "2099-01-01"})
    user = db.session.get(Order, order.id).user_id
    from app.models import User
    h = user_login(db.session.get(User, user).email)
    mine = client.get("/api/orders", headers=h).get_json()["orders"][0]
    assert mine["rider"] == {"name": "Admin", "phone": "09170000000"}
    assert mine["estimatedDelivery"] == "2099-01-01"


def test_the_customer_confirms_only_after_the_rider_delivered(client, make_order, make_user, make_product, user_login):
    user = make_user()
    h = user_login(user.email)
    product = make_product("Oil", price=100)
    shipped = make_order(user, [(product, 100, 1)], status="shipped")
    early = client.post(f"/api/orders/{shipped.id}/received", headers=h)
    assert early.status_code == 400
    assert Order.query.get(shipped.id).received_confirmed_at is None

    delivered = make_order(user, [(product, 100, 1)], status="delivered", received=False)
    listed = {o["id"]: o for o in client.get("/api/orders", headers=h).get_json()["orders"]}
    assert listed[delivered.id]["canReceive"] is True and listed[delivered.id]["tab"] == "to_receive"
    assert listed[delivered.id]["canReview"] is False  # rating opens once the customer confirms

    ok = client.post(f"/api/orders/{delivered.id}/received", headers=h)
    assert ok.status_code == 200 and ok.get_json()["order"]["canReceive"] is False
    assert ok.get_json()["order"]["receivedConfirmedAt"]
    assert ok.get_json()["order"]["canReview"] is True
    assert client.post(f"/api/orders/{delivered.id}/received", headers=h).status_code == 400


def test_an_admin_cannot_confirm_that_the_item_was_received(client, make_order, make_user, make_product, make_admin, admin_login):
    user = make_user()
    product = make_product("Oil", price=100)
    order = make_order(user, [(product, 100, 1)], status="delivered", received=False)
    make_admin()
    head = admin_login("head@example.com")
    assert client.post(f"/api/admin/orders/{order.id}/status", headers=head, json={"status": "delivered"}).status_code in (400, 409)
    assert client.post(f"/api/orders/{order.id}/received", headers=head).status_code in (401, 403, 404)
    assert Order.query.get(order.id).received_confirmed_at is None


def test_a_rider_account_needs_a_phone_number(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    body = {"name": "Ben", "email": "ben@example.com", "role": "Rider", "password": "Passw0rd!x", "confirmPassword": "x"}
    from conftest import PASSWORD
    body["confirmPassword"] = PASSWORD
    assert client.post("/api/admin/auth/accounts", headers=h, json=body).status_code == 400
    bad = client.post("/api/admin/auth/accounts", headers=h, json={**body, "phone": "abc"})
    assert bad.status_code == 400
    ok = client.post("/api/admin/auth/accounts", headers=h, json={**body, "phone": "0917 123 4567"})
    assert ok.status_code == 201 and ok.get_json()["admin"]["phone"] == "09171234567"
