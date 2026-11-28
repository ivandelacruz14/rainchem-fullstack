from datetime import datetime, timedelta

from app.extensions import db
from app.models import Admin, Notification, Order, User
from test_delivery_round4 import ready_order, riders


def _customer_headers(order, user_login):
    return user_login(db.session.get(User, order.user_id).email)


def _assign(client, head, order):
    rid = Admin.query.filter_by(email="rider@example.com").first().id
    return client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head,
                       json={"riderId": rid, "estimatedDate": "2099-01-01"})


def test_assigning_a_rider_notifies_the_customer(client, make_order, make_user, make_product, make_admin, admin_login, user_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    order.status = "confirmed"
    db.session.commit()
    head, rider, other = riders(make_admin, admin_login)
    assert _assign(client, head, order).status_code == 200
    h = _customer_headers(order, user_login)
    body = client.get("/api/notifications", headers=h).get_json()
    assert body["unread"] == 1 and "rider" in body["notifications"][0]["subject"].lower()
    client.post("/api/notifications/read", headers=h, json={})
    assert client.get("/api/notifications", headers=h).get_json()["unread"] == 0


def test_the_delivery_pin_is_saved_with_the_order_and_validated(client, make_user, make_product, user_login):
    user = make_user()
    h = user_login(user.email)
    product = make_product("Oil", price=100)
    base = {"items": [{"productId": product.id, "qty": 1}],
            "customer": {"name": "Ana", "phone": "09171234567", "email": user.email},
            "paymentMethod": "Cash on Delivery"}
    addr = {"line1": "Home: 1 Rizal St", "city": "Manila", "province": "Metro Manila", "region": "NCR", "zip": "1000"}
    bad = client.post("/api/orders", headers=h, json={**base, "address": {**addr, "latitude": 51.5, "longitude": -0.12}})
    assert bad.status_code == 400
    ok = client.post("/api/orders", headers=h, json={**base, "address": {**addr, "latitude": 14.5995, "longitude": 120.9842, "instructions": "Blue gate"}})
    assert ok.status_code == 201
    order = Order.query.get(ok.get_json()["order"]["id"])
    assert order.delivery_lat == 14.5995 and order.customer_instructions == "Blue gate"
    assert "14.5995,120.9842" in order.map_url


def test_the_map_link_falls_back_to_the_written_address(make_order, make_user, make_product):
    order, a, b = ready_order(make_order, make_user, make_product)
    assert order.delivery_lat is None and "google.com/maps" in order.map_url


def test_an_unconfirmed_delivery_is_confirmed_after_the_waiting_days(client, make_order, make_user, make_product, user_login, app):
    user = make_user()
    product = make_product("Oil", price=100)
    order = make_order(user, [(product, 100, 1)], status="delivered", received=False)
    for entry in order.history:
        if entry.status == "delivered":
            entry.changed_at = datetime.utcnow() - timedelta(days=app.config["AUTO_CONFIRM_DAYS"] + 1)
    db.session.commit()
    h = user_login(user.email)
    mine = client.get("/api/orders", headers=h).get_json()["orders"][0]
    assert mine["autoConfirmed"] is True and mine["canReceive"] is False
    assert Order.query.get(order.id).received_confirmed_at is not None


def test_a_reminder_is_sent_before_the_automatic_confirmation(client, make_order, make_user, make_product, user_login, app):
    user = make_user()
    product = make_product("Oil", price=100)
    order = make_order(user, [(product, 100, 1)], status="delivered", received=False)
    for entry in order.history:
        if entry.status == "delivered":
            entry.changed_at = datetime.utcnow() - timedelta(days=app.config["AUTO_CONFIRM_REMINDER_DAYS"], hours=1)
    db.session.commit()
    h = user_login(user.email)
    mine = client.get("/api/orders", headers=h).get_json()["orders"][0]
    assert mine["canReceive"] is True
    assert Notification.query.filter_by(user_id=user.id, channel="app").count() == 1


def test_the_cash_the_rider_collected_is_tracked_until_the_office_receives_it(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    rid = Admin.query.filter_by(email="rider@example.com").first().id
    order.rider_id = rid
    order.cod_amount = 250
    db.session.commit()
    cash = client.get("/api/rider/cash", headers=rider).get_json()
    assert cash["total"] == 250
    report = client.get("/api/admin/remittances", headers=head).get_json()
    row = next(r for r in report["riders"] if r["riderId"] == rid)
    assert row["outstanding"] == 250 and report["totals"]["outstanding"] >= 250
    got = client.post("/api/admin/remittances/receive", headers=head, json={"orderIds": [order.id]})
    assert got.status_code == 200 and got.get_json()["amount"] == 250
    assert client.get("/api/rider/cash", headers=rider).get_json()["total"] == 0
    assert client.post("/api/admin/remittances/receive", headers=head, json={"orderIds": [order.id]}).status_code == 400
    assert client.post("/api/admin/remittances/receive", headers=rider, json={"orderIds": [order.id]}).status_code in (401, 403)


def test_an_order_past_its_estimated_date_is_flagged(make_order, make_user, make_product):
    order, a, b = ready_order(make_order, make_user, make_product)
    order.rider_id = 1
    order.status = "shipped"
    order.estimated_delivery_date = (datetime.utcnow() - timedelta(days=2)).date()
    assert order.is_overdue is True
    order.estimated_delivery_date = (datetime.utcnow() + timedelta(days=2)).date()
    assert order.is_overdue is False
