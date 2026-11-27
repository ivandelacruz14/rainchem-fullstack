from app.extensions import db
from datetime import date, timedelta

from app.models import Order
from test_delivery_round4 import JPEG, assign, ready_order, riders, scan, upload
from test_delivery_rounds import setup_order, start


def test_the_order_sticker_confirms_the_order_before_and_during_delivery(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    qr = client.get(f"/api/admin/orders/{order.id}/sticker", headers=head).get_json()["sticker"]["qrText"]
    r = client.post(f"/api/rider/{order.id}/scan", headers=rider, json={"code": qr})
    assert r.status_code == 200 and r.get_json()["orderConfirmed"] is True
    assert client.post(f"/api/rider/{order.id}/scan", headers=rider, json={"code": order.order_number}).status_code == 200
    assert client.post(f"/api/rider/{order.id}/scan", headers=rider, json={"code": "RC-WRONG-9"}).status_code == 400
    start(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/scan", headers=rider, json={"code": order.order_number}).status_code == 200


def test_after_a_reschedule_every_unit_is_scanned_again(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    client.post(f"/api/rider/{order.id}/fail", headers=rider, json={"reason": "Road closed"})
    client.post(f"/api/admin/orders/{order.id}/confirm-failed", headers=head,
                json={"rescheduledFor": (date.today() + timedelta(days=1)).isoformat()})
    start(client, rider, order)
    upload(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 400   # units not scanned again
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 200


def test_the_delivery_note_is_saved_and_shown_to_the_admin(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    upload(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider, json={"note": "Left with the guard"}).status_code == 200
    row = next(o for o in client.get("/api/admin/delivered-orders", headers=head).get_json()["orders"] if o["id"] == order.id)
    assert row["deliveryNote"] == "Left with the guard" and row["hasPhoto"] is True
    assert row["riderName"] and row["deliveredAt"]


def test_a_product_without_a_barcode_is_flagged_for_the_office(client, make_order, make_user, make_product, make_admin, admin_login):
    from app.models import Product
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    pid = order.items[0].product_id
    Product.query.get(pid).barcode = None
    db.session.commit()
    detail = client.get(f"/api/rider/{order.id}", headers=rider).get_json()["order"]
    flagged = [m for m in detail["missing"] if m["productId"] == pid]
    assert flagged and flagged[0]["barcodeSet"] is False
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 400


def test_scanning_the_order_sticker_confirms_all_items_so_the_photo_and_delivery_can_follow(client, make_order, make_user, make_product, make_admin, admin_login):
    from app.extensions import db as _db
    from app.models import Product
    order, head, rider, other = setup_order(make_order, make_user, make_product, make_admin, admin_login, client)
    start(client, rider, order)
    pid = order.items[0].product_id
    Product.query.get(pid).barcode = None          # no item barcode at all
    _db.session.commit()
    qr = client.get(f"/api/admin/orders/{order.id}/sticker", headers=head).get_json()["sticker"]["qrText"]
    assert client.post(f"/api/rider/{order.id}/scan", headers=rider, json={"code": qr}).status_code == 200
    detail = client.get(f"/api/rider/{order.id}", headers=rider).get_json()["order"]
    assert detail["missing"] == []                 # every unit is confirmed
    upload(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 200

