from conftest import PASSWORD


def test_the_order_alert_counts_orders_waiting_for_confirmation(client, make_order, make_user, make_product, make_admin, admin_login):
    user = make_user()
    p = make_product("Oil", price=100, stock=50)
    make_order(user, [(p, 100, 1)], status="pending_confirmation", payment_status="unpaid")
    make_order(user, [(p, 100, 1)], status="confirmed", payment_status="unpaid")
    make_admin()
    make_admin("staff@example.com", "Support Staff", ["orders"])
    make_admin("rider@example.com", "Rider")
    body = client.get("/api/admin/orders/attention-count", headers=admin_login("head@example.com")).get_json()
    assert body["count"] == 1
    assert client.get("/api/admin/orders/attention-count", headers=admin_login("staff@example.com")).status_code == 200
    assert client.get("/api/admin/orders/attention-count", headers=admin_login("rider@example.com")).status_code == 403
