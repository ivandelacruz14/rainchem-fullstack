from app.extensions import db
from app.models import Admin, Order
from test_delivery_round4 import ready_order, riders


def make_confirmed(make_order, make_user, make_product):
    order, a, b = ready_order(make_order, make_user, make_product)
    order.status = "confirmed"
    db.session.commit()
    return order


def test_a_confirmed_order_goes_to_the_rider_in_one_step(client, make_order, make_user, make_product, make_admin, admin_login):
    order = make_confirmed(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    rid = Admin.query.filter_by(email="rider@example.com").first().id
    r = client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head, json={"riderId": rid, "estimatedDate": "2099-01-01"})
    assert r.status_code == 200
    fresh = Order.query.get(order.id)
    assert fresh.status == "ready_for_delivery" and fresh.rider_id == rid


def test_an_order_not_yet_confirmed_cannot_be_sent(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    order.status = "pending_confirmation"
    db.session.commit()
    head, rider, other = riders(make_admin, admin_login)
    rid = Admin.query.filter_by(email="rider@example.com").first().id
    assert client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head, json={"riderId": rid, "estimatedDate": "2099-01-01"}).status_code == 400


def test_the_dispatch_list_shows_the_order_until_a_rider_takes_it(client, make_order, make_user, make_product, make_admin, admin_login):
    order = make_confirmed(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    row = next(o for o in client.get("/api/admin/dispatch", headers=head).get_json()["orders"] if o["id"] == order.id)
    assert row["riderName"] is None and row["statusLabel"] == "Confirmed"
    rid = Admin.query.filter_by(email="rider@example.com").first().id
    client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head, json={"riderId": rid, "estimatedDate": "2099-01-01"})
    row = next(o for o in client.get("/api/admin/dispatch", headers=head).get_json()["orders"] if o["id"] == order.id)
    assert row["riderName"] and row["status"] == "ready_for_delivery"
    assert client.get("/api/admin/dispatch", headers=rider).status_code == 403
