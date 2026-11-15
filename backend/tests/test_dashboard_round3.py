from conftest import PASSWORD


def test_a_rider_and_a_developer_cannot_open_the_dashboard(client, make_admin, admin_login):
    make_admin("rider@example.com", "Rider")
    make_admin("dev@example.com", "Developer")
    assert client.get("/api/admin/overview", headers=admin_login("rider@example.com")).status_code == 403
    assert client.get("/api/admin/overview", headers=admin_login("dev@example.com")).status_code == 403


def test_the_money_figures_are_hidden_without_analytics(client, make_admin, admin_login):
    make_admin("staff@example.com", "Support Staff")
    body = client.get("/api/admin/overview", headers=admin_login("staff@example.com")).get_json()
    assert body["stats"]["totalRevenue"] is None and body["stats"]["saleOrderCount"] is None
    assert "orderCount" in body["stats"]


def test_the_head_admin_sees_the_money_figures(client, make_admin, admin_login):
    make_admin()
    body = client.get("/api/admin/overview", headers=admin_login("head@example.com")).get_json()
    assert body["stats"]["totalRevenue"] is not None
