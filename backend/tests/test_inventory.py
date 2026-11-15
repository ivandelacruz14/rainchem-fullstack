from sqlalchemy import text

from app.extensions import db
from app.models import AuditLog, InventoryAlert, InventoryMovement, Order, OrderStatusHistory, Product, SalesRecord
from app.services import inventory
from conftest import PASSWORD

URL = "/api/admin/inventory"


def head(make_admin, admin_login):
    make_admin()
    return admin_login("head@example.com")


def order_api(client, h, product, qty, method="Cash on Delivery"):
    r = client.post("/api/orders", headers=h, json={
        "items": [{"productId": product.id, "qty": qty}], "customer": {"name": "M", "phone": "09171234567", "email": "customer@example.com"},
        "address": {"line1": "a", "city": "b", "province": "c", "region": "d", "zip": "1"}, "paymentMethod": method})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["order"]


def types(product):
    return [(m.movement_type, m.quantity_change) for m in InventoryMovement.query.filter_by(product_id=product.id).order_by(InventoryMovement.id)]


def alerts(category=None):
    q = InventoryAlert.query
    return q.filter_by(category=category).all() if category else q.all()


def test_stock_changes_are_recorded_with_their_meaning(client, make_user, make_product, user_login, make_admin, admin_login):
    p = make_product(stock=50)
    assert types(p) == [("opening", 50)]
    user = make_user()
    order = order_api(client, user_login(user.email), p, 3)
    assert types(p)[-1] == ("sale", -3) and InventoryMovement.query.filter_by(movement_type="sale").one().order_id == order["id"]
    ah = head(make_admin, admin_login)
    client.post(f"/api/admin/orders/{order['id']}/status", headers=ah, json={"status": "cancelled"})
    assert types(p)[-1] == ("cancel_restore", 3)
    assert db.session.get(Product, p.id).stock == 50 == sum(q for _, q in types(p))


def test_customer_cancellation_and_approved_returns_restore_stock_in_the_history(client, make_user, make_product, user_login, make_admin, admin_login):
    p = make_product(stock=20)
    user = make_user()
    h = user_login(user.email)
    first = order_api(client, h, p, 2)
    client.post(f"/api/orders/{first['id']}/cancel", headers=h)
    assert types(p)[-1] == ("cancel_restore", 2)
    second = order_api(client, h, p, 4)
    ah = head(make_admin, admin_login)
    order = db.session.get(Order, second["id"])
    order.status, order.return_status = "delivered", "requested"
    db.session.commit()
    client.post(f"/api/admin/orders/{second['id']}/return/approve", headers=ah, json={})
    assert types(p)[-1] == ("return", 4)
    assert db.session.get(Product, p.id).stock == 20 and inventory.expected_stock()[p.id] == 20


def test_normal_activity_creates_no_false_alerts(client, make_user, make_product, user_login, make_admin, admin_login):
    p = make_product(stock=30)
    user = make_user()
    h = user_login(user.email)
    order = order_api(client, h, p, 2)
    other = order_api(client, h, p, 1)
    ah = head(make_admin, admin_login)
    client.post(f"/api/admin/orders/{order['id']}/status", headers=ah, json={"status": "cancelled"})
    client.post(f"{URL}/movements", headers=ah, json={"productId": p.id, "type": "received", "quantity": 10, "reason": "Delivery from supplier"})
    client.post(f"{URL}/movements", headers=ah, json={"productId": p.id, "type": "write_off", "quantity": 2, "reason": "Damaged in storage"})
    client.put(f"/api/products/{p.id}", headers=ah, json={"stock": 50, "stockReason": "Annual count"})
    assert inventory.run_scan() == []
    assert client.get(f"{URL}/alerts?refresh=1", headers=ah).get_json()["total"] == 0


def test_a_stock_figure_that_differs_from_the_history_is_flagged_with_the_real_numbers(client, make_admin, admin_login, make_product):
    p = make_product(stock=42)
    db.session.execute(text("UPDATE products SET stock = 39 WHERE id = :id"), {"id": p.id})   # a change that bypasses the app
    db.session.commit()
    ah = head(make_admin, admin_login)
    data = client.get(f"{URL}/alerts?refresh=1", headers=ah).get_json()
    alert = data["alerts"][0]
    assert alert["category"] == "stock_mismatch" and alert["productName"] == p.name
    assert (alert["expected"], alert["recorded"], alert["difference"]) == ("42", "39", "-3")
    assert alert["explanation"] == ("Inventory discrepancy detected: expected stock is 42 units, but the recorded stock is 39 units. "
                                    "Difference: -3 units. Review the stock movement history before applying a correction.")
    assert alert["status"] == "open" and alert["detectedAt"] and data["counts"] == {"open": 1, "under_review": 0, "resolved": 0}
    assert client.post(f"{URL}/scan", headers=ah).get_json()["created"] == 0                      # not duplicated on the next check
    assert InventoryAlert.query.count() == 1


def test_negative_stock_is_flagged(make_admin, make_product):
    p = make_product(stock=5)
    db.session.execute(text("UPDATE products SET stock = -2 WHERE id = :id"), {"id": p.id})
    db.session.commit()
    inventory.run_scan()
    assert {a.category for a in alerts()} == {"stock_mismatch", "negative_stock"}
    assert "-2 units" in alerts("negative_stock")[0].explanation


def test_duplicate_movements_and_repeated_order_processing_are_flagged(make_user, make_product, make_order):
    user, p = make_user(), make_product(stock=10)
    order = make_order(user, [(p, 10, 1)], status="confirmed")
    for _ in range(2):
        db.session.add(InventoryMovement(product_id=p.id, product_name=p.name, movement_type="sale", quantity_change=-1, order_id=order.id, actor_name="System"))
    db.session.add(OrderStatusHistory(order_id=order.id, status="confirmed"))
    db.session.add(OrderStatusHistory(order_id=order.id, status="confirmed"))
    db.session.commit()
    inventory.run_scan()
    dup = alerts("duplicate_movement")[0]
    assert (dup.expected_value, dup.recorded_value) == ("1", "2") and order.order_number in dup.explanation
    twice = alerts("order_processed_twice")[0]
    assert twice.recorded_value == "3" and "confirmed" in twice.explanation          # once from the fixture plus two repeats


def test_paid_without_a_payment_reference_is_flagged_only_when_it_should_be(make_user, make_product, make_order):
    user, p = make_user(), make_product()
    online = make_order(user, [(p, 10, 1)], status="confirmed", payment_status="paid")
    online.payment_method = "GCash"
    online.payment_reference = None
    cod = make_order(user, [(p, 10, 1)], status="delivered", payment_status="paid")
    traced = make_order(user, [(p, 10, 1)], status="confirmed", payment_status="paid")
    traced.payment_method, traced.payment_reference = "GCash", "pay_123"
    db.session.commit()
    inventory.run_scan()
    flagged = alerts("paid_without_reference")
    assert [a.order_id for a in flagged] == [online.id]                              # cash on delivery and traced payments are fine


def test_a_cancelled_order_that_did_not_restore_stock_is_flagged(client, make_user, make_product, user_login):
    p = make_product(stock=10)
    user = make_user()
    order = order_api(client, user_login(user.email), p, 4)
    row = db.session.get(Order, order["id"])
    row.status = "cancelled"                       # cancelled without going through the code that puts stock back
    db.session.commit()
    inventory.run_scan()
    found = alerts("cancelled_no_restore")[0]
    assert found.order_id == row.id and (found.expected_value, found.recorded_value) == ("0", "-4")


def test_unexplained_and_untracked_stock_changes_are_flagged(make_admin, make_product):
    p = make_product(stock=10)
    admin = make_admin()
    inventory.record_movement(p, "adjustment", -2, "", admin)            # no explanation
    inventory.record_movement(p, "adjustment", 1, "Recount", None)        # no signed-in administrator
    db.session.commit()
    p.stock = 100                                                          # changed with no recorded process at all
    db.session.commit()
    inventory.run_scan()
    assert len(alerts("adjustment_unexplained")) == 2
    assert "has no explanation" in alerts("adjustment_unexplained")[0].explanation
    assert len(alerts("untracked_change")) == 1 and "+91" in alerts("untracked_change")[0].explanation
    assert alerts("stock_mismatch") == []                                  # the history still adds up; the problem is the missing process


def test_a_sales_record_that_does_not_match_its_order_is_flagged(make_user, make_product, make_order):
    user, p = make_user(), make_product()
    order = make_order(user, [(p, 100, 2)], status="delivered", payment_status="paid")
    db.session.execute(text("UPDATE sales_records SET line_total = 50 WHERE order_id = :o"), {"o": order.id})
    gone = make_order(user, [(p, 10, 1)], status="delivered", payment_status="paid")
    SalesRecord.query.filter_by(order_id=gone.id).delete()
    db.session.commit()
    inventory.run_scan()
    mismatches = {a.order_id: a for a in alerts("sales_record_mismatch")}
    assert set(mismatches) == {order.id, gone.id}
    assert "PHP 200.00" in mismatches[order.id].explanation and "PHP 50.00" in mismatches[order.id].explanation
    assert "1 product line" in mismatches[gone.id].explanation


def test_review_note_and_resolve_workflow(client, make_admin, admin_login, make_product):
    p = make_product(stock=10)
    db.session.execute(text("UPDATE products SET stock = 8 WHERE id = :id"), {"id": p.id})
    db.session.commit()
    make_admin("staff@example.com", "Support Staff", ["products"])
    sh = admin_login("staff@example.com")
    alert_id = client.get(f"{URL}/alerts?refresh=1", headers=sh).get_json()["alerts"][0]["id"]
    detail = client.get(f"{URL}/alerts/{alert_id}", headers=sh).get_json()
    assert detail["stillApplies"] is True and detail["movements"][0]["type"] == "opening"
    assert client.post(f"{URL}/alerts/{alert_id}/review", headers=sh).get_json()["alert"]["assignedTo"] == "Admin"
    assert client.post(f"{URL}/alerts/{alert_id}/note", headers=sh, json={"note": ""}).status_code == 400
    assert client.post(f"{URL}/alerts/{alert_id}/note", headers=sh, json={"note": "Checking the shelf count"}).status_code == 200
    assert client.post(f"{URL}/alerts/{alert_id}/resolve", headers=sh, json={"note": ""}).status_code == 400
    done = client.post(f"{URL}/alerts/{alert_id}/resolve", headers=sh, json={"note": "Counted 8 on the shelf, damaged unit removed"}).get_json()["alert"]
    assert done["status"] == "resolved" and done["resolvedAt"] and "Checking the shelf count" in done["resolutionNote"]
    assert db.session.get(Product, p.id).stock == 8                                   # resolving never changes stock
    assert client.post(f"{URL}/alerts/{alert_id}/resolve", headers=sh, json={"note": "again"}).status_code == 409
    assert [h["action"] for h in client.get(f"{URL}/alerts/{alert_id}", headers=sh).get_json()["history"]] == ["alert_review_started", "alert_note", "alert_resolved"]


def test_alert_filters(client, make_admin, admin_login, make_product):
    a, b = make_product("A", stock=10), make_product("B", stock=10)
    db.session.execute(text("UPDATE products SET stock = 9 WHERE id = :id"), {"id": a.id})
    db.session.execute(text("UPDATE products SET stock = -1 WHERE id = :id"), {"id": b.id})
    db.session.commit()
    ah = head(make_admin, admin_login)
    q = lambda **kw: client.get(f"{URL}/alerts", headers=ah, query_string={"refresh": 1, **kw}).get_json()
    assert q()["total"] == 3
    assert q(category="negative_stock")["total"] == 1 and q(product_id=a.id)["total"] == 1
    assert q(status="unresolved")["total"] == 3 and q(status="resolved")["total"] == 0
    assert q(**{"from": "2020-01-01", "to": "2099-01-01"})["total"] == 3
    assert client.get(f"{URL}/alerts/count", headers=ah).get_json()["open"] == 3


def test_correction_changes_stock_only_through_an_audited_head_admin_action(client, make_admin, admin_login, make_product):
    p = make_product(stock=42)
    db.session.execute(text("UPDATE products SET stock = 39 WHERE id = :id"), {"id": p.id})
    db.session.commit()
    make_admin("staff@example.com", "Support Staff", ["products"])
    sh = admin_login("staff@example.com")
    ah = head(make_admin, admin_login) if False else None
    make_admin()
    ah = admin_login("head@example.com")
    alert_id = client.get(f"{URL}/alerts?refresh=1", headers=ah).get_json()["alerts"][0]["id"]
    body = {"mode": "align_to_history", "reason": "Recount found 42"}
    assert client.post(f"{URL}/alerts/{alert_id}/correct", headers=sh, json=body).status_code == 403
    assert db.session.get(Product, p.id).stock == 39
    assert client.post(f"{URL}/alerts/{alert_id}/correct", headers=ah, json={"mode": "align_to_history", "reason": ""}).status_code == 400
    assert client.post(f"{URL}/alerts/{alert_id}/correct", headers=ah, json={"mode": "other", "reason": "x"}).status_code == 400
    r = client.post(f"{URL}/alerts/{alert_id}/correct", headers=ah, json=body)
    assert r.status_code == 200 and r.get_json()["stock"] == 42 and r.get_json()["alert"]["status"] == "resolved"
    log = AuditLog.query.filter_by(action="stock_correction").one()
    assert (log.old_value, log.reason, log.admin_name) == ({"recordedStock": 39, "expectedStock": 42}, "Recount found 42", "Admin")
    assert log.new_value["recordedStock"] == 42 and log.created_at
    assert inventory.run_scan() == []                                                    # balanced again, no new alert
    assert client.post(f"{URL}/alerts/{alert_id}/correct", headers=ah, json=body).status_code == 409


def test_correction_can_instead_accept_the_recorded_stock(client, make_admin, admin_login, make_product):
    p = make_product(stock=10)
    db.session.execute(text("UPDATE products SET stock = 14 WHERE id = :id"), {"id": p.id})
    db.session.commit()
    ah = head(make_admin, admin_login)
    alert_id = client.get(f"{URL}/alerts?refresh=1", headers=ah).get_json()["alerts"][0]["id"]
    r = client.post(f"{URL}/alerts/{alert_id}/correct", headers=ah, json={"mode": "accept_recorded", "reason": "Supplier delivery was not logged"})
    assert r.status_code == 200 and db.session.get(Product, p.id).stock == 14                  # stock untouched
    assert types(p)[-1] == ("adjustment", 4) and inventory.expected_stock()[p.id] == 14
    assert AuditLog.query.filter_by(action="stock_correction").one().new_value["mode"] == "accept_recorded"


def test_only_stock_discrepancies_can_be_corrected_and_resolving_never_edits_orders(client, make_admin, admin_login, make_user, make_product, make_order):
    user, p = make_user(), make_product()
    order = make_order(user, [(p, 10, 1)], status="confirmed", payment_status="paid")
    order.payment_method, order.payment_reference = "GCash", None
    db.session.commit()
    ah = head(make_admin, admin_login)
    alert_id = client.get(f"{URL}/alerts?refresh=1", headers=ah).get_json()["alerts"][0]["id"]
    assert client.post(f"{URL}/alerts/{alert_id}/correct", headers=ah, json={"mode": "align_to_history", "reason": "x"}).status_code == 400
    client.post(f"{URL}/alerts/{alert_id}/resolve", headers=ah, json={"note": "Checked with the payment provider"})
    assert db.session.get(Order, order.id).payment_status == "paid"


def test_manual_stock_movements_need_a_head_admin_and_a_reason(client, make_admin, admin_login, make_product):
    p = make_product(stock=5)
    make_admin("staff@example.com", "Support Staff", ["products"])
    sh = admin_login("staff@example.com")
    ah = head(make_admin, admin_login)
    body = {"productId": p.id, "type": "received", "quantity": 5, "reason": "Supplier delivery"}
    assert client.post(f"{URL}/movements", headers=sh, json=body).status_code == 403
    assert client.post(f"{URL}/movements", headers=ah, json={**body, "reason": ""}).status_code == 400
    assert client.post(f"{URL}/movements", headers=ah, json={**body, "quantity": 0}).status_code == 400
    assert client.post(f"{URL}/movements", headers=ah, json={**body, "type": "sale"}).status_code == 400
    assert client.post(f"{URL}/movements", headers=ah, json={**body, "type": "write_off", "quantity": 99}).status_code == 400   # would go negative
    assert client.post(f"{URL}/movements", headers=ah, json=body).status_code == 201
    assert db.session.get(Product, p.id).stock == 10 and types(p)[-1] == ("received", 5)
    assert client.post(f"{URL}/movements", headers=ah, json={**body, "type": "write_off", "quantity": 3, "reason": "Leaked"}).status_code == 201
    assert types(p)[-1] == ("write_off", -3)
    listing = client.get(f"{URL}/movements?product_id={p.id}", headers=ah).get_json()
    assert listing["total"] == 3 and listing["movements"][0]["reason"] == "Leaked" and listing["movements"][0]["actor"] == "Admin"


def test_overview_shows_how_expected_stock_is_made_up(client, make_admin, admin_login, make_user, make_product, user_login):
    p = make_product(stock=20)
    user = make_user()
    order_api(client, user_login(user.email), p, 3)
    ah = head(make_admin, admin_login)
    client.post(f"{URL}/movements", headers=ah, json={"productId": p.id, "type": "received", "quantity": 5, "reason": "Delivery"})
    row = client.get(f"{URL}/overview", headers=ah).get_json()["products"][0]
    assert (row["opening"], row["received"], row["issued"], row["expected"], row["recorded"], row["difference"]) == (20, 5, 3, 22, 22, 0)


def test_an_approved_stock_edit_is_recorded_as_an_authorised_adjustment(client, make_admin, admin_login, make_product, approve):
    p = make_product(stock=10)
    ah = head(make_admin, admin_login)
    make_admin("staff@example.com", "Support Staff", ["products"])
    sh = admin_login("staff@example.com")
    rid = client.put(f"/api/products/{p.id}", headers=sh, json={"stock": 25, "stockReason": "Counted after delivery"}).get_json()["request"]["id"]
    assert db.session.get(Product, p.id).stock == 10 and len(types(p)) == 1
    assert approve(ah, rid).status_code == 200
    move = InventoryMovement.query.filter_by(movement_type="adjustment").one()
    assert (move.quantity_change, move.reason, move.reference) == (15, "Counted after delivery", f"change_request:{rid}")
    assert move.actor_admin_id is not None
    inventory.run_scan()
    assert alerts("adjustment_unexplained") == [] and alerts("stock_mismatch") == []


def test_inventory_screens_are_for_authorised_admins_only(client, make_admin, admin_login, make_user, user_login):
    user = make_user()
    make_admin("nope@example.com", "Support Staff", ["orders"])
    for url in (f"{URL}/overview", f"{URL}/alerts", f"{URL}/movements", f"{URL}/alerts/count", f"{URL}/audit"):
        assert client.get(url).status_code == 401, url
        assert client.get(url, headers=user_login(user.email)).status_code == 403, url
        assert client.get(url, headers=admin_login("nope@example.com")).status_code == 403, url
    assert client.post(f"{URL}/scan", headers=admin_login("nope@example.com")).status_code == 403


def test_a_deleted_product_keeps_its_history(client, make_admin, admin_login, make_product):
    p = make_product(stock=5)
    ah = head(make_admin, admin_login)
    assert client.delete(f"/api/products/{p.id}", headers=ah).status_code == 200
    move = InventoryMovement.query.one()
    assert move.product_id is None and move.product_name == p.name
    assert inventory.run_scan() == []
