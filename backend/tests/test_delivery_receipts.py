import base64
import io

from app.extensions import db
from app.models import Admin, AuditLog, Order
from app.models.delivery import DeliveryReceiptUpload
from test_delivery_round4 import JPEG, assign, ready_order, riders, scan, upload

PNG = b"\x89PNG\r\n\x1a\n" + b"s" * 80
SIG = "data:image/png;base64," + base64.b64encode(PNG).decode()


def shipped(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    return order, head, rider, other


def send_receipt(client, h, order, data=JPEG, name="receipt.jpg", signature=SIG, printed="Juan Dela Cruz", ack="yes"):
    body = {"file": (io.BytesIO(data), name), "signature": signature, "printedName": printed, "acknowledged": ack}
    return client.post(f"/api/rider/orders/{order.id}/receipt-upload", headers=h, data=body, content_type="multipart/form-data")


def test_the_receipt_is_built_from_the_stored_order(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    r = client.get(f"/api/rider/orders/{order.id}/receipt", headers=rider).get_json()["receipt"]
    assert r["orderNumber"] == order.order_number and r["barcodeValue"] == order.order_number
    assert r["customer"]["name"] == order.customer_name and r["customer"]["phone"] == order.customer_phone
    assert r["total"] == float(order.total) and r["subtotal"] == float(order.subtotal)
    assert len(r["items"]) == 2 and {i["quantity"] for i in r["items"]} == {2, 1}
    assert r["payment"]["isPaid"] is True and r["payment"]["codAmountToCollect"] == 0.0


def test_the_qr_holds_no_customer_details_and_verifies_only_when_untampered(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    text = client.get(f"/api/rider/orders/{order.id}/receipt", headers=rider).get_json()["receipt"]["qrText"]
    assert order.customer_name not in text and order.customer_phone not in text
    assert client.post("/api/receipts/verify", headers=head, json={"code": text}).status_code == 200
    forged = text.rsplit("|", 1)[0] + "|0000000000000000"
    assert client.post("/api/receipts/verify", headers=head, json={"code": forged}).status_code == 404


def test_qr_image_is_a_png_and_only_for_the_assigned_rider(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    r = client.get(f"/api/rider/orders/{order.id}/receipt/qr.png", headers=rider)
    assert r.status_code == 200 and r.data[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get(f"/api/rider/orders/{order.id}/receipt/qr.png", headers=other).status_code == 404


def test_upload_needs_the_signature_the_name_and_acknowledgement(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    assert send_receipt(client, rider, order, signature=None).status_code == 400
    assert send_receipt(client, rider, order, printed="").status_code == 400
    assert send_receipt(client, rider, order, ack="no").status_code == 400


def test_upload_rejects_fake_files_and_oversize_files(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    assert send_receipt(client, rider, order, data=b"<html>not a receipt</html>", name="receipt.jpg").status_code == 400
    assert send_receipt(client, rider, order, data=b"%PDF-1.4 " + b"x" * 50, name="receipt.pdf").status_code == 201
    from app.models.delivery import DeliveryReceiptUpload as U
    U.query.delete()
    db.session.commit()
    client.application.config["RECEIPT_MAX_MB"] = 1
    try:
        assert send_receipt(client, rider, order, data=JPEG + b"x" * (1024 * 1024 + 10)).status_code == 413
    finally:
        client.application.config["RECEIPT_MAX_MB"] = 5


def test_one_receipt_at_a_time_and_a_rejected_one_can_be_replaced(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    first = send_receipt(client, rider, order).get_json()["upload"]
    assert send_receipt(client, rider, order).status_code == 409                 # still waiting for review
    assert client.post(f"/api/admin/delivery-confirmations/{first['id']}/reject", headers=head,
                       json={"reason": "Signature is missing"}).status_code == 200
    second = send_receipt(client, rider, order)
    assert second.status_code == 201 and second.get_json()["upload"]["status"] == "pending_verification"


def test_reject_needs_a_reason_and_verify_only_once(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    row = send_receipt(client, rider, order).get_json()["upload"]
    assert client.post(f"/api/admin/delivery-confirmations/{row['id']}/reject", headers=head, json={"reason": "no"}).status_code == 400
    assert client.post(f"/api/admin/delivery-confirmations/{row['id']}/verify", headers=head).status_code == 200
    assert client.post(f"/api/admin/delivery-confirmations/{row['id']}/verify", headers=head).status_code == 409


def test_the_admin_tabs_follow_the_review_status(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    tab = lambda t: client.get(f"/api/admin/delivery-confirmations?status={t}", headers=head).get_json()["items"]
    assert [i["orderNumber"] for i in tab("pending_confirmation")] == [order.order_number]
    row = send_receipt(client, rider, order).get_json()["upload"]
    assert tab("pending_confirmation") == [] and len(tab("pending_verification")) == 1
    client.post(f"/api/admin/delivery-confirmations/{row['id']}/verify", headers=head)
    assert len(tab("verified")) == 1 and tab("pending_verification") == []


def test_the_file_and_signature_are_only_for_staff_who_can_see_orders(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    row = send_receipt(client, rider, order).get_json()["upload"]
    f = client.get(f"/api/admin/delivery-confirmations/{row['id']}/file", headers=head)
    assert f.status_code == 200 and f.data == JPEG and "sandbox" in f.headers["Content-Security-Policy"]
    assert client.get(f"/api/admin/delivery-confirmations/{row['id']}/signature.png", headers=head).data == PNG
    assert client.get(f"/api/admin/delivery-confirmations/{row['id']}/file", headers=rider).status_code == 403


def test_a_delivery_waits_for_the_verified_receipt(client, make_order, make_user, make_product, make_admin, admin_login):
    client.application.config["POD_REQUIRE_VERIFIED_RECEIPT"] = True
    try:
        order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
        for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
            scan(client, rider, order, code)
        upload(client, rider, order)
        assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 400
        row = send_receipt(client, rider, order).get_json()["upload"]
        assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 400   # pending review
        client.post(f"/api/admin/delivery-confirmations/{row['id']}/verify", headers=head)
        assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 200
        assert Order.query.get(order.id).status == "delivered"
    finally:
        client.application.config["POD_REQUIRE_VERIFIED_RECEIPT"] = False


def test_every_receipt_action_is_audited(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = shipped(client, make_order, make_user, make_product, make_admin, admin_login)
    row = send_receipt(client, rider, order).get_json()["upload"]
    client.post(f"/api/admin/delivery-confirmations/{row['id']}/verify", headers=head)
    actions = {e.action for e in AuditLog.query.all()}
    assert {"receipt_uploaded", "receipt_verified"} <= actions
