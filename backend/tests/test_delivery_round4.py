import io

from app.extensions import db
from app.models import Admin, Order
from conftest import PASSWORD

JPEG = b"\xff\xd8\xff\xe0" + b"x" * 64 + b"\xff\xd9"
PNG_AS_JPG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


def ready_order(make_order, make_user, make_product, lines=((2,),), status="ready_for_delivery", payment="paid"):
    user = make_user()
    a = make_product("Oil", price=100, stock=50)
    a.barcode = "RC-OIL-1"
    b = make_product("Filter", price=50, stock=50)
    b.barcode = "RC-FIL-1"
    db.session.commit()
    order = make_order(user, [(a, 100, 2), (b, 50, 1)], status=status, payment_status=payment)
    return order, a, b


def riders(make_admin, admin_login):
    make_admin()
    make_admin("rider@example.com", "Rider")
    make_admin("rider2@example.com", "Rider")
    make_admin("staff@example.com", "Support Staff")
    return admin_login("head@example.com"), admin_login("rider@example.com"), admin_login("rider2@example.com")


def assign(client, head, order, rider_email):
    rid = Admin.query.filter_by(email=rider_email).first().id
    return client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head, json={"riderId": rid})


def scan(client, h, order, code):
    return client.post(f"/api/rider/{order.id}/scan", headers=h, json={"code": code})


def upload(client, h, order, data=JPEG, name="proof.jpg"):
    return client.post(f"/api/rider/{order.id}/proof", headers=h,
                       data={"image": (io.BytesIO(data), name)}, content_type="multipart/form-data")


def test_only_a_rider_can_be_assigned_and_only_when_ready(client, make_order, make_user, make_product, make_admin, admin_login):
    order, _, _ = ready_order(make_order, make_user, make_product)
    head, rider, _ = riders(make_admin, admin_login)
    staff_id = Admin.query.filter_by(email="staff@example.com").first().id
    assert client.post(f"/api/admin/orders/{order.id}/assign-rider", headers=head, json={"riderId": staff_id}).status_code == 400
    assert assign(client, head, order, "rider@example.com").status_code == 200
    assert Order.query.get(order.id).rider_id is not None


def test_a_rider_sees_only_their_own_orders(client, make_order, make_user, make_product, make_admin, admin_login):
    order, _, _ = ready_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    assert client.get(f"/api/rider/{order.id}", headers=rider).status_code == 200
    assert client.get(f"/api/rider/{order.id}", headers=other).status_code == 404
    assert client.get("/api/rider", headers=other).get_json()["orders"] == []


def test_wrong_and_foreign_codes_are_rejected_and_do_not_count(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    assert scan(client, rider, order, "NOT-A-CODE").status_code == 422
    stranger = make_product("Stranger", price=10, stock=5)
    stranger.barcode = "RC-STR-9"
    db.session.commit()
    r = scan(client, rider, order, "RC-STR-9")
    assert r.status_code == 422 and "not part of this order" in r.get_json()["message"]
    assert r.get_json()["order"]["missing"]                       # nothing counted


def test_a_product_cannot_be_scanned_more_times_than_it_is_ordered(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, _ = ready_order(make_order, make_user, make_product)
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    assert scan(client, rider, order, "RC-OIL-1").status_code == 200
    assert scan(client, rider, order, "RC-OIL-1").status_code == 200       # two of two
    r = scan(client, rider, order, "RC-OIL-1")
    assert r.status_code == 422 and "already scanned" in r.get_json()["message"]


def test_delivery_is_blocked_until_every_unit_and_the_proof_are_in(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    r = client.post(f"/api/rider/{order.id}/deliver", headers=rider)
    assert r.status_code == 400 and r.get_json()["missing"]
    scan(client, rider, order, "RC-OIL-1")
    scan(client, rider, order, "RC-OIL-1")
    r = client.post(f"/api/rider/{order.id}/deliver", headers=rider)
    assert r.status_code == 400 and r.get_json()["missing"][0]["name"] == "Filter"    # the filter is still missing
    scan(client, rider, order, "RC-FIL-1")
    r = client.post(f"/api/rider/{order.id}/deliver", headers=rider)
    assert r.status_code == 400 and "proof" in r.get_json()["error"].lower()
    assert Order.query.get(order.id).status == "shipped"


def test_proof_must_be_a_real_image_and_cannot_be_replaced(client, make_order, make_user, make_product, make_admin, admin_login):
    order, _, _ = ready_order(make_order, make_user, make_product)
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    assert upload(client, rider, order, data=PNG_AS_JPG, name="proof.jpg").status_code in (400, 415, 422)
    assert upload(client, rider, order).status_code == 201
    assert upload(client, rider, order).status_code == 409


def test_a_full_delivery_completes_and_then_cannot_be_changed(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    assert upload(client, rider, order).status_code == 201
    r = client.post(f"/api/rider/{order.id}/deliver", headers=rider)
    assert r.status_code == 200 and r.get_json()["order"]["status"] == "delivered"
    from app.models import OrderStatusHistory
    assert OrderStatusHistory.query.filter_by(order_id=order.id, status="delivered").count() == 1
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 400   # cannot confirm twice
    assert client.post(f"/api/admin/orders/{order.id}/status", headers=head, json={"status": "cancelled"}).status_code == 409
    assert client.post(f"/api/admin/orders/{order.id}/status", headers=head, json={"status": "shipped"}).status_code == 409


def test_cash_on_delivery_is_recorded_as_paid_when_delivered(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product, payment="unpaid")
    o = Order.query.get(order.id)
    o.payment_method = "Cash on Delivery"
    db.session.commit()
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    upload(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 200
    assert Order.query.get(order.id).payment_status == "paid"


def test_an_online_order_that_is_not_paid_cannot_be_delivered(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product, payment="unpaid")
    o = Order.query.get(order.id)
    o.payment_method = "GCash"
    db.session.commit()
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    upload(client, rider, order)
    r = client.post(f"/api/rider/{order.id}/deliver", headers=rider)
    assert r.status_code == 400 and "not been paid" in r.get_json()["error"]


def test_the_admin_cannot_set_out_for_delivery_or_delivered_directly(client, make_order, make_user, make_product, make_admin, admin_login):
    order, _, _ = ready_order(make_order, make_user, make_product, status="processing")
    head, _, _ = riders(make_admin, admin_login)
    assert client.post(f"/api/admin/orders/{order.id}/status", headers=head, json={"status": "delivered"}).status_code == 400
    assert client.post(f"/api/admin/orders/{order.id}/status", headers=head, json={"status": "shipped"}).status_code == 400


def test_a_correction_needs_the_head_admin_and_a_reason(client, make_order, make_user, make_product, make_admin, admin_login):
    order, _, _ = ready_order(make_order, make_user, make_product)
    head, rider, _ = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    upload(client, rider, order)
    client.post(f"/api/rider/{order.id}/deliver", headers=rider)
    staff = admin_login("staff@example.com")
    assert client.post(f"/api/admin/orders/{order.id}/delivery-correction", headers=staff, json={"status": "shipped", "reason": "x"}).status_code == 403
    assert client.post(f"/api/admin/orders/{order.id}/delivery-correction", headers=head, json={"status": "shipped"}).status_code == 400
    r = client.post(f"/api/admin/orders/{order.id}/delivery-correction", headers=head, json={"status": "shipped", "reason": "Rider marked it by mistake"})
    assert r.status_code == 200 and r.get_json()["order"]["status"] == "shipped"
    from app.models import AuditLog
    entry = AuditLog.query.filter_by(action="delivery_correction").one()
    assert entry.old_value == {"status": "delivered"} and entry.reason == "Rider marked it by mistake"


def test_barcodes_are_unique(client, make_user, make_product, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    a = make_product("One", price=10, stock=5)
    b = make_product("Two", price=10, stock=5)
    a.barcode = "RC-SAME-1"
    db.session.commit()
    r = client.put(f"/api/products/{b.id}", headers=h, json={"barcode": "RC-SAME-1"})
    assert r.status_code == 400 and "already uses this barcode" in str(r.get_json())
