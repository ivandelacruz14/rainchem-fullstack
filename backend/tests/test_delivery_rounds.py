from datetime import date, timedelta

from app.models import Order
from test_delivery_round4 import JPEG, assign, ready_order, riders, upload


def setup_order(make_order, make_user, make_product, make_admin, admin_login, client):
    order, a, b = ready_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    return order, head, rider, other


def start(client, rider, order):
    return client.post(f"/api/rider/{order.id}/start", headers=rider)


def test_summary_counts_the_riders_own_orders(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    s = client.get("/api/rider/summary", headers=rider).get_json()["summary"]
    assert (s["total"], s["pending"], s["outForDelivery"]) == (1, 1, 0)
    start(client, rider, order)
    s = client.get("/api/rider/summary", headers=rider).get_json()["summary"]
    assert (s["pending"], s["outForDelivery"]) == (0, 1)
    assert client.get("/api/rider/summary", headers=other).get_json()["summary"]["total"] == 0


def test_search_finds_by_name_order_number_or_phone_and_only_the_riders_orders(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    first_name = order.customer_name.split()[0]
    digits = "".join(c for c in order.customer_phone if c.isdigit())
    for q in (first_name, order.order_number, digits[-6:]):
        found = client.get("/api/rider/search", headers=rider, query_string={"q": q}).get_json()["orders"]
        assert [o["id"] for o in found] == [order.id], q
    assert client.get("/api/rider/search", headers=other, query_string={"q": first_name}).get_json()["orders"] == []
    assert client.get("/api/rider/search", headers=rider, query_string={"q": "zzzz-no-match"}).get_json()["orders"] == []
    assert client.get("/api/rider/search", headers=rider, query_string={"q": "a"}).get_json()["orders"] == []


def test_failed_needs_an_out_for_delivery_order_and_a_reason(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    assert client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "Traffic"}).status_code == 400  # not started
    start(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "no"}).status_code == 400
    r = client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "Traffic jam on EDSA"})
    assert r.status_code == 200 and r.get_json()["order"]["status"] == "delivery_failed"


def test_the_customer_sees_the_failed_reason_and_the_new_date(client, make_order, make_user, make_product, make_admin, admin_login, user_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "Emergency in the area"})
    cust = user_login("customer@example.com")
    mine = next(o for o in client.get("/api/orders", headers=cust).get_json()["orders"] if o["id"] == order.id)
    assert mine["statusLabel"] == "Delivery failed" and mine["failedReason"] == "Emergency in the area"
    new_day = (date.today() + timedelta(days=2)).isoformat()
    client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head, json={"rescheduledFor": new_day})
    mine = next(o for o in client.get("/api/orders", headers=cust).get_json()["orders"] if o["id"] == order.id)
    assert mine["statusLabel"] == "Rescheduled" and mine["rescheduledFor"] == new_day


def test_admin_confirms_the_failure_with_a_future_date_only(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "Customer not home"})
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head, json={"rescheduledFor": yesterday}).status_code == 400
    assert client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head, json={"rescheduledFor": "not-a-date"}).status_code == 400
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head, json={"rescheduledFor": tomorrow}).status_code == 200
    assert client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head, json={"rescheduledFor": tomorrow}).status_code == 400  # already confirmed


def test_the_failed_list_shows_awaiting_then_rescheduled(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "Road closed"})
    awaiting = client.get("/api/admin/failed-deliveries", headers=head, query_string={"tab": "awaiting"}).get_json()["items"]
    assert [i["orderNumber"] for i in awaiting] == [order.order_number] and awaiting[0]["failedReason"] == "Road closed"
    client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head,
                json={"rescheduledFor": (date.today() + timedelta(days=1)).isoformat()})
    assert client.get("/api/admin/failed-deliveries", headers=head, query_string={"tab": "awaiting"}).get_json()["items"] == []
    assert len(client.get("/api/admin/failed-deliveries", headers=head, query_string={"tab": "rescheduled"}).get_json()["items"]) == 1


def test_a_rescheduled_order_goes_out_again_and_delivers_with_the_photo(client, make_order, make_user, make_product, make_admin, admin_login):
    from test_delivery_round4 import scan
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "Customer not home"})
    client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head,
                json={"rescheduledFor": (date.today() + timedelta(days=1)).isoformat()})
    assert start(client, rider, order).status_code == 200
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 400   # no photo yet
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    upload(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 200
    assert Order.query.get(order.id).status == "delivered"


def test_admins_cannot_set_failed_statuses_by_hand(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    r = client.post(f"/api/admin/orders/{order.id}/status", headers=head, json={"status": "delivery_failed"})
    assert r.status_code == 400


def test_the_sticker_is_for_admins_and_shows_cod_or_paid(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    s = client.get(f"/api/admin/orders/{order.id}/sticker", headers=head).get_json()["sticker"]
    assert s["orderNumber"] == order.order_number and s["qrText"].startswith("RCPT|") and s["barcodeValue"] == order.order_number
    assert s["customer"]["name"] == order.customer_name and s["payment"]["method"]
    assert client.get(f"/api/admin/orders/{order.id}/sticker", headers=rider).status_code == 403
