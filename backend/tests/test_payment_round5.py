from app.extensions import db
from app.models import Order
from conftest import PASSWORD


def gcash_order(make_order, make_user, make_product, status="pending_confirmation", payment="verifying", reference=None):
    from app.models import User
    user = User.query.filter_by(email="customer@example.com").first() or make_user()
    p = make_product("Oil", price=100, stock=50)
    o = make_order(user, [(p, 100, 1)], status=status, payment_status=payment)
    row = Order.query.get(o.id)
    row.payment_method = "GCash"
    row.payment_reference = reference
    db.session.commit()
    return row, user


def test_one_gcash_reference_cannot_confirm_two_orders(client, make_order, make_user, make_product, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    first, _ = gcash_order(make_order, make_user, make_product, reference="GC-778812")
    assert client.post(f"/api/admin/orders/{first.id}/payment/verify", headers=h).status_code == 200
    second, _ = gcash_order(make_order, make_user, make_product, reference="GC-778812")
    r = client.post(f"/api/admin/orders/{second.id}/payment/verify", headers=h)
    assert r.status_code == 409 and first.order_number in r.get_json()["error"]
    assert Order.query.get(second.id).payment_status == "verifying"


def test_an_unpaid_order_gets_no_official_receipt(client, make_order, make_user, make_product, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    order, _ = gcash_order(make_order, make_user, make_product, status="confirmed", payment="verifying", reference="GC-1")
    r = client.get(f"/api/receipts/admin/orders/{order.id}.pdf", headers=h)
    assert r.status_code == 400 and "verified as paid" in r.get_json()["error"]


def test_a_paid_order_gets_a_pdf_receipt_for_its_owner_only(client, make_order, make_user, make_product, make_admin, admin_login, user_login):
    make_admin()
    order, owner = gcash_order(make_order, make_user, make_product, status="confirmed", payment="paid", reference="GC-9")
    make_user("other@example.com", "Other Person")
    r = client.get(f"/api/receipts/orders/{order.id}.pdf", headers=user_login(owner.email))
    assert r.status_code == 200 and r.headers["Content-Type"] == "application/pdf"
    assert r.data.startswith(b"%PDF") and len(r.data) > 1000
    assert "attachment" in r.headers["Content-Disposition"]
    stranger = client.get(f"/api/receipts/orders/{order.id}.pdf", headers=user_login("other@example.com"))
    assert stranger.status_code == 404


def test_the_receipt_cannot_be_downloaded_twice_as_a_new_record(client, make_order, make_user, make_product, make_admin, admin_login):
    from app.models import Receipt
    make_admin()
    h = admin_login("head@example.com")
    order, _ = gcash_order(make_order, make_user, make_product, status="confirmed", payment="paid", reference="GC-10")
    client.get(f"/api/receipts/admin/orders/{order.id}.pdf", headers=h)
    client.get(f"/api/receipts/admin/orders/{order.id}.pdf", headers=h)
    assert Receipt.query.filter_by(order_id=order.id).count() == 1


def test_order_lists_page_ten_rows_when_a_page_is_asked_for(client, make_order, make_user, make_product, make_admin, admin_login, user_login):
    user = make_user()
    p = make_product("Oil", price=100, stock=500)
    for _ in range(12):
        make_order(user, [(p, 100, 1)], status="pending_confirmation", payment_status="unpaid")
    make_admin()
    h = admin_login("head@example.com")
    r = client.get("/api/admin/orders?page=1", headers=h).get_json()
    assert len(r["orders"]) == 10 and r["page"] == {"page": 1, "perPage": 10, "total": 12, "pages": 2}
    assert len(client.get("/api/admin/orders?page=2", headers=h).get_json()["orders"]) == 2
    mine = client.get("/api/orders?page=1", headers=user_login(user.email)).get_json()
    assert len(mine["orders"]) == 10 and mine["page"]["total"] == 12
    assert len(client.get("/api/orders", headers=user_login(user.email)).get_json()["orders"]) == 12   # no page asked: everything, as before


def test_admin_customer_list_pages_in_tens(client, make_user, make_admin, admin_login):
    for i in range(11):
        make_user(f"c{i}@example.com", f"Customer {i}")
    make_admin()
    h = admin_login("head@example.com")
    body = client.get("/api/admin/users?page=1", headers=h).get_json()
    assert len(body["users"]) == 10 and body["page"]["total"] >= 11 and body["page"]["pages"] >= 2
    assert "page" not in client.get("/api/admin/users", headers=h).get_json()
