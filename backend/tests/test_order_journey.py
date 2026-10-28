from datetime import datetime, timedelta

from app.extensions import db
from app.models import OrderStatusHistory


def journey_of(client, h, order):
    r = client.get(f"/api/orders/track/{order.tracking_number}", headers=h)
    assert r.status_code == 200
    return r.get_json()["order"]["journey"]


def states(journey):
    return {m["key"]: m["state"] for m in journey["milestones"]}


def at(order, status, minutes):
    db.session.add(OrderStatusHistory(order_id=order.id, status=status, changed_at=order.created_at + timedelta(minutes=minutes)))
    db.session.commit()


def make(make_user, make_product, make_order, **kw):
    user = make_user()
    return user, make_order(user, [(make_product("Oil"), 100, 2)], **kw)


def test_new_cod_order_is_waiting_for_verification(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="pending_confirmation", payment_status="unpaid")
    j = journey_of(client, user_login(user.email), order)
    assert states(j) == {"received": "done", "verification": "current", "approved": "upcoming",
                         "preparing": "upcoming", "in_transit": "upcoming", "delivered": "upcoming"}
    assert j["headline"] == "Order Verification" and j["state"] == "in_progress" and j["stageNumber"] == 2 and j["stageCount"] == 6
    assert j["alerts"] == [] and j["updatedAt"]


def test_every_real_status_advances_exactly_one_stage(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="pending_confirmation")
    h = user_login(user.email)
    expected = [
        ("confirmed", "approved", ["received", "verification"]),
        ("processing", "preparing", ["received", "verification", "approved"]),
        ("shipped", "in_transit", ["received", "verification", "approved", "preparing"]),
    ]
    for minutes, (status, current, done) in enumerate(expected, start=1):
        order.status = status
        at(order, status, minutes)
        j = journey_of(client, h, order)
        s = states(j)
        assert s[current] == "current", status
        assert [k for k, v in s.items() if v == "done"] == done, status
        assert all(v == "upcoming" for k, v in s.items() if k not in done + [current])
    order.status = "delivered"
    at(order, "delivered", 4)
    j = journey_of(client, h, order)
    assert set(states(j).values()) == {"done"} and j["state"] == "completed" and j["headline"] == "Delivered"


def test_in_transit_and_delivered_only_show_when_the_status_says_so(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="processing")
    j = journey_of(client, user_login(user.email), order)
    by_key = {m["key"]: m for m in j["milestones"]}
    for key in ("in_transit", "delivered"):
        assert by_key[key]["state"] == "upcoming" and by_key[key]["at"] is None


def test_times_come_from_the_database_and_nothing_is_invented(client, make_user, make_product, make_order, user_login):
    created = datetime(2026, 10, 20, 8, 0, 0)
    user, order = make(make_user, make_product, make_order, status="pending_confirmation", created_at=created)
    order.confirmed_at = created + timedelta(hours=2)
    order.status = "shipped"
    at(order, "confirmed", 120)
    at(order, "shipped", 300)
    OrderStatusHistory.query.filter_by(order_id=order.id, status="pending_confirmation").update({"changed_at": created})
    db.session.commit()
    j = journey_of(client, user_login(user.email), order)
    by_key = {m["key"]: m for m in j["milestones"]}
    assert by_key["received"]["at"] == created.isoformat()
    assert by_key["approved"]["at"] == (created + timedelta(hours=2)).isoformat()
    assert by_key["in_transit"]["at"] == (created + timedelta(minutes=300)).isoformat()
    assert by_key["preparing"]["at"] is None and by_key["delivered"]["at"] is None          # never happened, so no time
    assert j["updatedAt"] == (created + timedelta(minutes=300)).isoformat()
    text = str(j).lower()
    assert "estimated" not in text and "courier" not in text and "eta" not in text.split()


def test_cancelled_order_stops_where_it_was_and_shows_why(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="cancelled")
    order.cancelled_at = order.created_at + timedelta(hours=1)
    db.session.commit()
    j = journey_of(client, user_login(user.email), order)
    assert states(j) == {"received": "done", "verification": "stopped", "approved": "upcoming",
                         "preparing": "upcoming", "in_transit": "upcoming", "delivered": "upcoming"}
    assert j["state"] == "cancelled" and j["headline"] == "Cancelled"
    assert j["alerts"][0]["kind"] == "cancelled" and j["alerts"][0]["at"] == order.cancelled_at.isoformat()


def test_order_cancelled_after_approval_keeps_its_earlier_stages(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="cancelled")
    at(order, "confirmed", 30)
    j = journey_of(client, user_login(user.email), order)
    assert states(j)["approved"] == "stopped" and states(j)["verification"] == "done"
    assert states(j)["in_transit"] == "upcoming"


def test_payment_problems_are_shown_instead_of_advancing(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="pending_confirmation", payment_status="unpaid")
    order.payment_method = "GCash"
    db.session.commit()
    h = user_login(user.email)
    j = journey_of(client, h, order)
    assert states(j)["verification"] == "current" and states(j)["approved"] == "upcoming"
    assert j["alerts"][0]["title"] == "Payment needed"
    assert "payment" in [m for m in j["milestones"] if m["key"] == "verification"][0]["description"].lower()

    order.payment_status = "verifying"
    order.payment_submitted_at = order.created_at + timedelta(minutes=10)
    db.session.commit()
    j = journey_of(client, h, order)
    assert j["alerts"][0]["title"] == "Verifying your payment" and states(j)["verification"] == "current"
    assert [m for m in j["milestones"] if m["key"] == "verification"][0]["at"] == order.payment_submitted_at.isoformat()


def test_refund_and_return_states_are_shown(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="delivered", return_status="requested")
    at(order, "delivered", 5)
    order.return_requested_at = order.created_at + timedelta(days=1)
    db.session.commit()
    h = user_login(user.email)
    j = journey_of(client, h, order)
    assert j["state"] == "completed" and [a["title"] for a in j["alerts"]] == ["Return requested"]
    order.return_status = "approved"
    order.payment_status = "refund_pending"
    db.session.commit()
    assert [a["title"] for a in journey_of(client, h, order)["alerts"]] == ["Refund pending", "Return approved"]
    order.payment_status = "refunded"
    order.return_status = "rejected"
    db.session.commit()
    assert [a["title"] for a in journey_of(client, h, order)["alerts"]] == ["Refunded", "Return rejected"]


def test_the_same_status_everywhere(client, make_user, make_product, make_order, user_login, make_admin, admin_login):
    user, order = make(make_user, make_product, make_order, status="shipped")
    at(order, "shipped", 5)
    h = user_login(user.email)
    mine = client.get("/api/orders", headers=h).get_json()["orders"][0]
    tracked = client.get(f"/api/orders/track/{order.tracking_number}", headers=h).get_json()["order"]
    make_admin()
    admin_side = client.get("/api/admin/orders", headers=admin_login("head@example.com")).get_json()["orders"][0]
    assert mine["status"] == tracked["status"] == admin_side["status"] == "shipped"
    assert mine["journey"]["headline"] == tracked["journey"]["headline"] == admin_side["journey"]["headline"] == "In Transit"


def test_customers_can_only_track_their_own_orders_and_the_response_stays_private(client, make_user, make_product, make_order, user_login):
    user, order = make(make_user, make_product, make_order, status="shipped")
    other = make_user("o@example.com", "Other Person")
    assert client.get(f"/api/orders/track/{order.tracking_number}", headers=user_login(other.email)).status_code == 404
    assert client.get(f"/api/orders/track/{order.tracking_number}").status_code == 401
    assert client.get(f"/api/orders/track/{order.order_number}", headers=user_login(user.email)).status_code == 200  # order number works too
