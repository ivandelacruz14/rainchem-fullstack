from app.extensions import db
from conftest import days_ago


def seed(make_user, make_product, make_order):
    user = make_user()
    a, b, c = make_product("Alpha", price=100), make_product("Beta", price=50), make_product("Gamma (never sold)", price=10)
    make_order(user, [(a, 100, 2)], created_at=days_ago(1))                       # counts: 200
    make_order(user, [(a, 100, 1), (b, 50, 4)], created_at=days_ago(2), status="processing")  # 100 + 200
    make_order(user, [(b, 50, 9)], status="pending_confirmation", payment_status="unpaid", created_at=days_ago(1))
    make_order(user, [(a, 100, 5)], status="cancelled", created_at=days_ago(1))
    make_order(user, [(a, 100, 7)], return_status="approved", payment_status="refund_pending", created_at=days_ago(1))
    make_order(user, [(b, 50, 3)], created_at=days_ago(12))                        # previous period only
    return a, b, c


def report(client, headers, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    r = client.get(f"/api/admin/analytics/report?{query}", headers=headers)
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def test_only_recorded_sales_are_counted(client, make_admin, admin_login, make_user, make_product, make_order):
    seed(make_user, make_product, make_order)
    make_admin()
    from datetime import datetime, timedelta
    today = (datetime.utcnow() + timedelta(hours=8)).date()
    data = report(client, admin_login("head@example.com"), granularity="daily",
                  start=(today - timedelta(days=6)).isoformat(), end=today.isoformat())
    assert data["summary"] == {"revenue": 500.0, "units": 7, "orders": 2, "averageOrderValue": 250.0}
    assert len(data["series"]) == 7
    assert sum(d["revenue"] for d in data["series"]) == 500.0
    by_name = {p["name"]: p for p in data["products"]}
    assert by_name["Alpha"]["units"] == 3 and by_name["Alpha"]["revenue"] == 300.0
    assert by_name["Gamma (never sold)"]["units"] == 0
    assert data["lowestSelling"][0]["name"] == "Gamma (never sold)"
    assert data["bestSelling"][0]["name"] == "Beta"  # 4 units vs 3


def test_previous_period_comparison_and_no_made_up_percentages(client, make_admin, admin_login, make_user, make_product, make_order):
    seed(make_user, make_product, make_order)
    make_admin()
    from datetime import datetime, timedelta
    today = (datetime.utcnow() + timedelta(hours=8)).date()
    h = admin_login("head@example.com")
    data = report(client, h, granularity="weekly", start=(today - timedelta(days=6)).isoformat(), end=today.isoformat())
    assert data["previous"]["revenue"] == 150.0
    assert data["change"]["revenue"] == round((500 - 150) / 150 * 100, 1)
    empty = report(client, h, start=(today - timedelta(days=400)).isoformat() if False else (today - timedelta(days=60)).isoformat(),
                   end=(today - timedelta(days=50)).isoformat())
    assert empty["change"]["revenue"] is None


def test_grouping_and_validation(client, make_admin, admin_login):
    make_admin()
    h = admin_login("head@example.com")
    monthly = report(client, h, granularity="monthly", start="2026-01-15", end="2026-03-10")
    assert [m["label"] for m in monthly["series"]] == ["Jan 2026", "Feb 2026", "Mar 2026"]
    weekly = report(client, h, granularity="weekly", start="2026-10-05", end="2026-10-18")
    assert len(weekly["series"]) == 2 and weekly["series"][0]["start"] == "2026-10-05"
    for params in ("start=2026-03-10&end=2026-01-01", "granularity=hourly", "start=abc", "start=2020-01-01&end=2026-01-01"):
        assert client.get(f"/api/admin/analytics/report?{params}", headers=h).status_code == 400, params


def test_distributor_only_sees_their_own_products(client, make_admin, admin_login, make_user, make_product, make_order):
    d = make_admin("d@example.com", "Distributor", ["analytics", "orders"])
    make_admin()
    user = make_user()
    mine, theirs = make_product("Mine", price=100, owner=d), make_product("Theirs", price=100)
    make_order(user, [(mine, 100, 1), (theirs, 100, 5)], created_at=days_ago(1))
    h = admin_login("d@example.com")
    data = report(client, h, granularity="daily")
    assert data["summary"]["revenue"] == 100.0
    assert [p["name"] for p in data["products"]] == ["Mine"]
    assert client.get(f"/api/admin/analytics/products/{theirs.id}/history", headers=h).status_code == 403
    assert client.get(f"/api/admin/analytics/products/{mine.id}/history", headers=h).status_code == 200

    orders = client.get("/api/admin/orders", headers=h).get_json()
    assert orders["scope"] == "limited" and orders["orders"][0]["subtotal"] == 100.0
    flat = str(orders)
    assert "customer@example.com" not in flat and "09171234567" not in flat and "Theirs" not in flat


def test_product_history(client, make_admin, admin_login, make_user, make_product, make_order):
    a, *_ = seed(make_user, make_product, make_order)
    make_admin()
    r = client.get(f"/api/admin/analytics/products/{a.id}/history?granularity=daily", headers=admin_login("head@example.com"))
    body = r.get_json()
    assert body["summary"]["units"] == 3 and body["product"]["name"] == "Alpha"


def test_forecast_needs_enough_history(client, make_admin, admin_login, make_user, make_product, make_order):
    user = make_user()
    p = make_product("Fast", stock=5)
    make_order(user, [(p, 500, 1)], created_at=days_ago(3))
    make_admin()
    data = client.get("/api/admin/analytics/insights", headers=admin_login("head@example.com")).get_json()
    assert data["enoughHistory"] is False
    assert data["products"][0]["status"] == "not_enough_data"
    assert data["suggestions"] == [] and "not guarantees" in data["disclaimer"]


def test_forecast_estimate_restock_and_slow_mover(client, make_admin, admin_login, make_user, make_product, make_order):
    user = make_user()
    fast = make_product("Fast", price=100, stock=4)
    slow = make_product("Slow", price=100, stock=80)
    make_order(user, [(slow, 100, 1)], created_at=days_ago(70))  # shop history exists, slow product then stops selling
    for week in range(1, 8):
        for n in range(2):
            make_order(user, [(fast, 100, 3)], created_at=days_ago(week * 7 - n))
    make_admin()
    data = client.get("/api/admin/analytics/insights", headers=admin_login("head@example.com")).get_json()
    assert data["enoughHistory"] is True
    items = {p["name"]: p for p in data["products"]}
    assert items["Fast"]["status"] == "estimate"
    assert items["Fast"]["estimatedWeeklyUnits"] > 0
    assert items["Fast"]["estimateLow"] <= items["Fast"]["estimatedUnitsNext30Days"] <= items["Fast"]["estimateHigh"]
    assert items["Slow"]["status"] == "no_recent_sales"
    kinds = {(s["type"], s["name"]) for s in data["suggestions"]}
    assert ("restock", "Fast") in kinds and ("promote", "Slow") in kinds


def test_overview_scopes_by_role(client, make_admin, admin_login, make_user, make_product, make_order):
    make_admin()
    d = make_admin("d@example.com", "Distributor", ["products"])
    user = make_user()
    make_order(user, [(make_product("HQ", price=100), 100, 2)], created_at=days_ago(1))
    full = client.get("/api/admin/overview", headers=admin_login("head@example.com")).get_json()
    limited = client.get("/api/admin/overview", headers=admin_login("d@example.com")).get_json()
    assert full["scope"] == "full" and full["stats"]["totalRevenue"] == 200.0 and "userCount" in full["stats"]
    assert limited["scope"] == "limited" and limited["stats"]["totalRevenue"] == 0 and "userCount" not in limited["stats"]
