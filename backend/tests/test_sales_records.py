from datetime import datetime, timedelta

from sqlalchemy import text

from app.extensions import db
from app.models import AuditLog, Order, SalesRecord
from app.services import sales_ledger
from conftest import PASSWORD, days_ago

URL = "/api/admin/sales-records"


def head(make_admin, admin_login):
    make_admin()
    return admin_login("head@example.com")


def place(client, h, items, method="Cash on Delivery"):
    r = client.post("/api/orders", headers=h, json={
        "items": items, "customer": {"name": "Maria Santos", "phone": "09171234567", "email": "customer@example.com"},
        "address": {"line1": "a", "city": "b", "province": "c", "region": "d", "zip": "1"}, "paymentMethod": method,
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()["order"]


def test_an_order_creates_one_record_per_product_line_automatically(client, make_user, make_product, user_login, make_admin, admin_login):
    user = make_user()
    a, b = make_product("Oil A", price=100, stock=50), make_product("Oil B", price=200, stock=50)
    order = place(client, user_login(user.email), [{"productId": a.id, "qty": 2}, {"productId": b.id, "qty": 1}])
    rows = SalesRecord.query.order_by(SalesRecord.id).all()
    assert len(rows) == 2
    first, second = rows
    assert (first.product_name, first.quantity, float(first.unit_price), float(first.line_total)) == ("Oil A", 2, 100.0, 200.0)
    assert (second.product_name, second.quantity, float(second.line_total)) == ("Oil B", 1, 200.0)
    assert first.order_number == order["orderNumber"] and first.customer_name == "Maria Santos" and first.customer_id == user.id
    assert first.state == "pending" and first.payment_method == "Cash on Delivery"          # not paid yet, so not a completed sale
    assert float(first.order_total) == float(second.order_total) == order["total"]
    assert float(first.shipping_share + second.shipping_share) == order["shippingFee"]       # shipping adds up exactly
    assert first.sku == f"RC-{a.id:04d}" and first.category == "Oils & Fluids"


def test_records_follow_the_order_through_payment_and_delivery(client, make_user, make_product, user_login, make_admin, admin_login):
    user = make_user()
    p = make_product(price=100, stock=50)
    order = place(client, user_login(user.email), [{"productId": p.id, "qty": 1}])
    make_admin()
    ah = admin_login("head@example.com")
    assert SalesRecord.query.one().state == "pending"
    assert client.post(f"/api/admin/orders/{order['id']}/confirm", headers=ah).status_code == 200
    assert SalesRecord.query.one().state == "pending"                                       # confirmed COD is still unpaid
    client.post(f"/api/admin/orders/{order['id']}/status", headers=ah, json={"status": "shipped"})
    client.post(f"/api/admin/orders/{order['id']}/status", headers=ah, json={"status": "delivered"})
    row = SalesRecord.query.one()
    assert row.state == "completed" and row.payment_status == "paid" and row.fulfillment_status == "Delivered"
    assert SalesRecord.query.count() == 1                                                    # still a single row


def test_cancelled_refunded_and_returned_orders_are_shown_accurately(make_user, make_product, make_order):
    user, p = make_user(), make_product()
    cancelled = make_order(user, [(p, 100, 1)], status="cancelled", payment_status="unpaid")
    refunded = make_order(user, [(p, 100, 1)], status="cancelled", payment_status="refund_pending")
    returned = make_order(user, [(p, 100, 1)], status="delivered", return_status="approved", payment_status="paid")
    paid = make_order(user, [(p, 100, 1)], status="delivered", payment_status="paid")
    unpaid = make_order(user, [(p, 100, 1)], status="pending_confirmation", payment_status="unpaid")
    states = {r.order_id: r.state for r in SalesRecord.query.all()}
    assert states == {cancelled.id: "cancelled", refunded.id: "refunded", returned.id: "returned", paid.id: "completed", unpaid.id: "pending"}


def test_repeating_events_never_duplicate_records(make_user, make_product, make_order):
    user, p = make_user(), make_product()
    order = make_order(user, [(p, 100, 2), (make_product("Two"), 50, 1)], status="confirmed", payment_status="paid")
    for _ in range(3):
        order.payment_status = "paid"                       # the same payment event arriving again
        db.session.commit()
        sales_ledger.sync_order(db.session, order.id)
        db.session.commit()
    sales_ledger.sync_all()
    sales_ledger.sync_all()
    assert SalesRecord.query.count() == 2
    unique = db.session.execute(text("SELECT COUNT(DISTINCT order_item_id) FROM sales_records")).scalar()
    assert unique == 2


def test_the_price_at_the_time_of_sale_is_kept_when_prices_change(make_user, make_product, make_order):
    user, p = make_user(), make_product(price=100)
    make_order(user, [(p, 100, 2)], status="delivered", payment_status="paid")
    p.price = 999
    p.name = "Renamed"
    db.session.commit()
    row = SalesRecord.query.one()
    assert float(row.unit_price) == 100 and float(row.line_total) == 200 and row.product_name == "RAIMOL Oil"


def test_discounts_are_split_out(client, make_user, make_product, user_login, make_admin, admin_login):
    user = make_user()
    p = make_product(price=100, stock=100)
    make_admin()
    ah = admin_login("head@example.com")
    client.post("/api/admin/sales", headers=ah, json={"productIds": [p.id], "percent": 30,
                "startDate": dates_today(), "endDate": dates_today()})
    place(client, user_login(user.email), [{"productId": p.id, "qty": 2}])
    row = SalesRecord.query.one()
    assert (float(row.list_unit_price), float(row.unit_price)) == (100.0, 70.0)
    assert (float(row.subtotal), float(row.discount_amount), float(row.line_total)) == (200.0, 60.0, 140.0)


def dates_today():
    from app.services.sales_analytics import local_today
    return local_today().isoformat()


def test_rows_are_listed_filtered_sorted_and_paged(client, make_admin, admin_login, make_user, make_product, make_order):
    user, other = make_user(), make_user("o@example.com", "Ben Cruz")
    a, b = make_product("Alpha Oil", price=100), make_product("Beta Coolant", price=50, category="Coolant")
    make_order(user, [(a, 100, 3)], status="delivered", payment_status="paid", created_at=days_ago(5))
    make_order(other, [(b, 50, 1)], status="delivered", payment_status="paid", created_at=days_ago(2))
    make_order(user, [(b, 50, 4)], status="cancelled", payment_status="unpaid", created_at=days_ago(1))
    h = head(make_admin, admin_login)
    data = client.get(URL, headers=h).get_json()
    assert data["total"] == 3 and len(data["records"]) == 3 and data["totals"]["units"] == 8
    assert [r["productName"] for r in data["records"]] == ["Beta Coolant", "Beta Coolant", "Alpha Oil"]       # newest first
    q = lambda **kw: client.get(URL, headers=h, query_string=kw).get_json()
    assert q(q="ben")["total"] == 1 and q(q="alpha")["total"] == 1 and q(q=data["records"][0]["orderNumber"])["total"] == 1
    assert q(q=f"RC-{a.id:04d}")["total"] == 1                                                              # search by SKU
    assert q(category="Coolant")["total"] == 2 and q(product_id=a.id)["total"] == 1
    assert q(state="completed")["total"] == 2 and q(state="cancelled")["total"] == 1
    assert q(order_status="cancelled")["total"] == 1 and q(payment_status="paid")["total"] == 2
    start = (datetime.utcnow() + timedelta(hours=8) - timedelta(days=3)).date().isoformat()
    assert q(**{"from": start})["total"] == 2
    assert [r["quantity"] for r in q(sort="quantity", dir="asc")["records"]] == [1, 3, 4]
    assert [r["lineTotal"] for r in q(sort="total", dir="desc")["records"]] == [300.0, 200.0, 50.0]
    page = q(per_page=5, page=1)
    assert page["page"] == 1 and page["pages"] == 1
    assert client.get(URL, headers=h, query_string={"from": "nope"}).status_code == 400
    assert q(q="no such thing")["records"] == []


def test_pagination_on_a_larger_set(client, make_admin, admin_login, make_user, make_product, make_order):
    user, p = make_user(), make_product()
    for _ in range(12):
        make_order(user, [(p, 10, 1)], status="delivered", payment_status="paid")
    h = head(make_admin, admin_login)
    first = client.get(URL, headers=h, query_string={"per_page": 5, "page": 1}).get_json()
    last = client.get(URL, headers=h, query_string={"per_page": 5, "page": 3}).get_json()
    assert first["total"] == 12 and first["pages"] == 3 and len(first["records"]) == 5 and len(last["records"]) == 2
    assert {r["id"] for r in first["records"]}.isdisjoint({r["id"] for r in last["records"]})


def test_summary_separates_gross_discounts_refunds_and_net(client, make_admin, admin_login, make_user, make_product, make_order):
    user, p = make_user(), make_product(price=100)
    make_order(user, [(p, 80, 5)], status="delivered", payment_status="paid", created_at=days_ago(1))   # list 100 (rate 0.2): gross 500, discount 100, net 400
    make_order(user, [(p, 100, 2)], status="cancelled", payment_status="refund_pending", created_at=days_ago(1))
    make_order(user, [(p, 100, 1)], status="pending_confirmation", payment_status="unpaid", created_at=days_ago(1))
    from app.models import OrderItem
    OrderItem.query.filter_by(quantity=5).update({"discount_rate": 0.2})
    db.session.commit()
    sales_ledger.sync_all()
    h = head(make_admin, admin_login)
    data = client.get(f"{URL}/summary", headers=h, query_string={"granularity": "daily"}).get_json()
    s = data["summary"]
    assert s["completedRows"] == 1 and s["units"] == 5 and s["completedValue"] == 400.0
    assert s["grossSales"] == 700.0 and s["discounts"] == 100.0 and s["refunds"] == 200.0 and s["netSales"] == 400.0
    assert s["pendingRows"] == 1 and s["pendingValue"] == 100.0 and s["cancelledRows"] == 0 and s["refundedRows"] == 1
    assert "not profit" in data["definitions"]["netSales"]
    assert sum(point["netSales"] for point in data["series"]) == 400.0 and len(data["series"]) == 30
    assert data["bestSelling"][0]["units"] == 5
    assert client.get(f"{URL}/summary?granularity=hourly", headers=h).status_code == 400


def test_summary_finds_products_with_declining_sales(client, make_admin, admin_login, make_user, make_product, make_order):
    user = make_user()
    falling, rising = make_product("Falling"), make_product("Rising")
    make_order(user, [(falling, 10, 10)], status="delivered", payment_status="paid", created_at=days_ago(40))
    make_order(user, [(falling, 10, 2)], status="delivered", payment_status="paid", created_at=days_ago(5))
    make_order(user, [(rising, 10, 1)], status="delivered", payment_status="paid", created_at=days_ago(40))
    make_order(user, [(rising, 10, 9)], status="delivered", payment_status="paid", created_at=days_ago(5))
    h = head(make_admin, admin_login)
    start = (datetime.utcnow() + timedelta(hours=8) - timedelta(days=29)).date().isoformat()
    data = client.get(f"{URL}/summary", headers=h, query_string={"from": start, "granularity": "weekly"}).get_json()
    assert [d["name"] for d in data["declining"]] == ["Falling"] and data["declining"][0]["changePercent"] == -80.0


def test_csv_export_opens_in_excel_and_respects_filters(client, make_admin, admin_login, make_user, make_product, make_order):
    user = make_user("=cmd@example.com", "=HYPERLINK(\"x\")")
    p = make_product("Plain Oil")
    q = make_product("Cool")
    make_order(user, [(p, 100, 1)], status="delivered", payment_status="paid")
    make_order(user, [(q, 50, 1)], status="delivered", payment_status="paid")
    h = head(make_admin, admin_login)
    r = client.get(f"{URL}/export.csv", headers=h, query_string={"q": "plain"})
    assert r.status_code == 200 and r.mimetype == "text/csv" and "attachment" in r.headers["Content-Disposition"]
    body = r.data.decode("utf-8")
    assert body.startswith("\ufeffRecord ID,Order,") and "Plain Oil" in body and "Cool" not in body.split("\n", 1)[1]
    assert "'=HYPERLINK" in body and ",=HYPERLINK" not in body                                     # no formula injection
    entry = AuditLog.query.filter_by(action="sales_export").one()
    assert entry.new_value["rows"] == 1


def test_only_authorised_admins_can_view_or_export(client, make_admin, admin_login, make_user, user_login, make_product, make_order):
    user, p = make_user(), make_product()
    make_order(user, [(p, 10, 1)], status="delivered", payment_status="paid")
    make_admin("staff@example.com", "Support Staff")                 # no analytics permission by default
    make_admin("analyst@example.com", "Support Staff", ["analytics"])
    for url in (URL, f"{URL}/summary", f"{URL}/export.csv", f"{URL}/1"):
        assert client.get(url).status_code == 401, url
        assert client.get(url, headers=user_login(user.email)).status_code == 403, url
        assert client.get(url, headers=admin_login("staff@example.com")).status_code == 403, url
        assert client.get(url, headers=admin_login("analyst@example.com")).status_code == 200, url
    analyst = admin_login("analyst@example.com")
    assert client.post(f"{URL}/1/correction", headers=analyst, json={}).status_code == 403            # head only
    assert client.post(f"{URL}/reconcile", headers=analyst).status_code == 403


def test_amounts_cannot_be_edited_through_the_api(client, make_admin, admin_login, make_user, make_product, make_order):
    user, p = make_user(), make_product()
    make_order(user, [(p, 100, 1)], status="delivered", payment_status="paid")
    h = head(make_admin, admin_login)
    for method in ("put", "patch", "delete"):
        assert getattr(client, method)(f"{URL}/1", headers=h, json={"lineTotal": 1}).status_code == 405
    rejected = client.post(f"{URL}/1/correction", headers=h, json={"field": "lineTotal", "value": "1", "reason": "x"})
    assert rejected.status_code == 400 and float(SalesRecord.query.one().line_total) == 100.0


def test_controlled_correction_needs_a_reason_and_is_audited(client, make_admin, admin_login, make_user, make_product, make_order):
    user, p = make_user(), make_product()
    order = make_order(user, [(p, 100, 1)], status="delivered", payment_status="paid")
    h = head(make_admin, admin_login)
    path = f"{URL}/1/correction"
    assert client.post(path, headers=h, json={"field": "category", "value": "Brakes", "reason": ""}).status_code == 400
    ok = client.post(path, headers=h, json={"field": "category", "value": "Brakes", "reason": "Wrong category at the time"})
    assert ok.status_code == 200 and ok.get_json()["record"]["category"] == "Brakes" and ok.get_json()["record"]["corrected"] is True
    log = AuditLog.query.filter_by(action="sales_record_correction").one()
    assert (log.admin_name, log.old_value, log.new_value, log.reason) == ("Admin", {"category": "Oils & Fluids"}, {"category": "Brakes"}, "Wrong category at the time")
    assert log.created_at
    # a later change to the order does not wipe the correction
    db.session.get(Order, order.id).payment_status = "paid"
    db.session.get(Order, order.id).status = "shipped"
    db.session.commit()
    assert SalesRecord.query.one().category == "Brakes"
    detail = client.get(f"{URL}/1", headers=h).get_json()
    assert len(detail["corrections"]) == 1 and detail["order"]["orderNumber"] == order.order_number and len(detail["lines"]) == 1


def test_reconcile_rebuilds_missing_rows_from_orders(client, make_admin, admin_login, make_user, make_product, make_order):
    user, p = make_user(), make_product()
    make_order(user, [(p, 100, 1)], status="delivered", payment_status="paid")
    SalesRecord.query.delete()
    db.session.commit()
    h = head(make_admin, admin_login)
    assert client.post(f"{URL}/reconcile", headers=h).get_json() == {"orders": 1, "records": 1}
    assert client.post(f"{URL}/reconcile", headers=h).get_json()["records"] == 1


def test_a_rolled_back_order_leaves_no_record(client, make_user, make_product, user_login):
    user = make_user()
    p = make_product(stock=1)
    r = client.post("/api/orders", headers=user_login(user.email), json={
        "items": [{"productId": p.id, "qty": 5}], "customer": {"name": "M", "phone": "09171234567", "email": "customer@example.com"},
        "address": {"line1": "a", "city": "b", "province": "c", "region": "d", "zip": "1"}, "paymentMethod": "Cash on Delivery"})
    assert r.status_code == 400 and SalesRecord.query.count() == 0 and Order.query.count() == 0
