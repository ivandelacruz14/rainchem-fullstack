from datetime import datetime, timedelta

from app.extensions import db
from app.models import ProductSale
from app.services.sales_analytics import local_today


def day(offset):
    return (local_today() + timedelta(days=offset)).isoformat()


def create_sale(client, headers, product_ids, percent=30, start=0, end=0, label="Sale"):
    return client.post("/api/admin/sales", headers=headers, json={
        "productIds": product_ids, "percent": percent, "startDate": day(start), "endDate": day(end), "label": label,
    })


def listing(client):
    return {p["name"]: p for p in client.get("/api/products").get_json()["products"]}


def test_sale_shows_original_and_sale_price_to_visitors(client, make_admin, admin_login, make_product):
    make_admin()
    p = make_product("Oil", price=500)
    other = make_product("No sale", price=200)
    assert create_sale(client, admin_login("head@example.com"), [p.id]).status_code == 201
    item = listing(client)["Oil"]
    assert item["price"] == 500 and item["onSale"] is True
    assert item["salePercent"] == 30 and item["salePrice"] == 350.0 and item["saleLabel"] == "Sale"
    assert listing(client)["No sale"]["onSale"] is False and listing(client)["No sale"]["salePrice"] is None


def test_scheduled_sale_is_not_active_until_it_starts(client, make_admin, admin_login, make_product):
    make_admin()
    p = make_product("Oil", price=500)
    r = create_sale(client, admin_login("head@example.com"), [p.id], start=7, end=13)
    assert r.get_json()["sales"][0]["status"] == "scheduled"
    assert listing(client)["Oil"]["onSale"] is False


def test_sale_window_covers_the_whole_last_day_in_shop_time(client, make_admin, admin_login, make_product):
    make_admin()
    p = make_product("Oil", price=500)
    create_sale(client, admin_login("head@example.com"), [p.id], start=0, end=0)
    sale = ProductSale.query.one()
    assert sale.ends_at - sale.starts_at == timedelta(days=1)
    assert sale.status(sale.starts_at) == "active"
    assert sale.status(sale.ends_at - timedelta(seconds=1)) == "active"
    assert sale.status(sale.ends_at) == "ended"


def test_checkout_charges_the_sale_price_and_ignores_the_browser(client, make_admin, admin_login, make_product, make_user, user_login):
    make_admin()
    p = make_product("Oil", price=500, stock=50)
    create_sale(client, admin_login("head@example.com"), [p.id], percent=30)
    make_user()
    h = user_login("customer@example.com")
    cart = client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 2, "price": 1}).get_json()
    assert cart["items"][0]["unitPrice"] == 350.0 and cart["summary"]["subtotal"] == 700.0
    assert cart["summary"]["savings"] == 300.0
    order = client.post("/api/orders", headers=h, json={
        "items": [{"productId": p.id, "qty": 2, "unitPrice": 1, "price": 1}],
        "customer": {"name": "M", "phone": "09171234567", "email": "customer@example.com"},
        "address": {"line1": "a", "city": "b", "province": "c", "region": "d", "zip": "1"},
        "paymentMethod": "Cash on Delivery",
    })
    assert order.status_code == 201
    body = order.get_json()["order"]
    assert body["subtotal"] == 700.0
    assert body["items"][0]["unitPrice"] == 350.0 and body["items"][0]["discountRate"] == 0.3


def test_sale_and_bulk_discount_do_not_stack_best_one_wins(client, make_admin, admin_login, make_product, make_user, user_login):
    make_admin()
    p = make_product("Oil", price=100, stock=100)
    make_user()
    h = user_login("customer@example.com")
    # No sale: 10 units get the 10% bulk discount.
    assert client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 10}).get_json()["items"][0]["unitPrice"] == 90.0
    create_sale(client, admin_login("head@example.com"), [p.id], percent=5)
    assert client.get("/api/cart", headers=h).get_json()["items"][0]["unitPrice"] == 90.0   # bulk 10% beats sale 5%
    ProductSale.query.delete()
    db.session.commit()
    create_sale(client, admin_login("head@example.com"), [p.id], percent=40)
    assert client.get("/api/cart", headers=h).get_json()["items"][0]["unitPrice"] == 60.0   # sale 40% beats bulk 10%


def test_validation(client, make_admin, admin_login, make_product):
    make_admin()
    p = make_product("Oil")
    h = admin_login("head@example.com")
    bad = [
        dict(percent=0), dict(percent=91), dict(percent="abc"), dict(percent=12.5),
        dict(start=-1, end=0), dict(start=3, end=1), dict(start=0, end=400),
    ]
    for kwargs in bad:
        assert create_sale(client, h, [p.id], **kwargs).status_code == 400, kwargs
    assert client.post("/api/admin/sales", headers=h, json={"productIds": [], "percent": 10, "startDate": day(0), "endDate": day(0)}).status_code == 400
    assert client.post("/api/admin/sales", headers=h, json={"productIds": [9999], "percent": 10, "startDate": day(0), "endDate": day(0)}).status_code == 400
    assert client.post("/api/admin/sales", headers=h, json={"productIds": [p.id], "percent": 10, "startDate": "x", "endDate": "y"}).status_code == 400
    assert ProductSale.query.count() == 0


def test_overlapping_sales_on_the_same_product_are_refused(client, make_admin, admin_login, make_product):
    make_admin()
    p, q = make_product("A"), make_product("B")
    h = admin_login("head@example.com")
    assert create_sale(client, h, [p.id], start=0, end=6).status_code == 201
    assert create_sale(client, h, [p.id, q.id], start=3, end=9).status_code == 400
    assert ProductSale.query.count() == 1  # nothing was half-created for product B
    assert create_sale(client, h, [p.id], start=7, end=13).status_code == 201   # back to back is fine


def test_several_products_in_one_go(client, make_admin, admin_login, make_product):
    make_admin()
    a, b = make_product("A", price=100), make_product("B", price=200)
    r = create_sale(client, admin_login("head@example.com"), [a.id, b.id], percent=25)
    assert [s["salePrice"] for s in r.get_json()["sales"]] == [75.0, 150.0]


def test_end_sale_now_and_cancel_scheduled(client, make_admin, admin_login, make_product):
    make_admin()
    p = make_product("Oil", price=500)
    h = admin_login("head@example.com")
    running = create_sale(client, h, [p.id], start=0, end=6).get_json()["sales"][0]
    assert client.post(f"/api/admin/sales/{running['id']}/end", headers=h).get_json()["sale"]["status"] == "ended"
    assert listing(client)["Oil"]["onSale"] is False
    assert client.post(f"/api/admin/sales/{running['id']}/end", headers=h).status_code == 400
    later = create_sale(client, h, [p.id], start=5, end=8).get_json()["sales"][0]
    assert client.post(f"/api/admin/sales/{later['id']}/end", headers=h).get_json()["sale"]["status"] == "ended"
    assert ProductSale.query.count() == 2  # history kept


def test_edit_percent_and_dates(client, make_admin, admin_login, make_product):
    make_admin()
    p = make_product("Oil", price=500)
    h = admin_login("head@example.com")
    running = create_sale(client, h, [p.id], start=0, end=2).get_json()["sales"][0]
    r = client.put(f"/api/admin/sales/{running['id']}", headers=h, json={"percent": 50, "endDate": day(4)})
    assert r.status_code == 200 and r.get_json()["sale"]["salePrice"] == 250.0
    assert client.put(f"/api/admin/sales/{running['id']}", headers=h, json={"startDate": day(1)}).status_code == 400
    assert listing(client)["Oil"]["salePrice"] == 250.0
    scheduled = create_sale(client, h, [p.id], start=10, end=12).get_json()["sales"][0]
    moved = client.put(f"/api/admin/sales/{scheduled['id']}", headers=h, json={"startDate": day(11), "endDate": day(14)})
    assert moved.status_code == 200 and moved.get_json()["sale"]["startDate"] == day(11)


def test_distributor_can_only_sell_own_products_on_sale(client, make_admin, admin_login, make_product):
    d1 = make_admin("d1@example.com", "Distributor", ["products"])
    d2 = make_admin("d2@example.com", "Distributor", ["products"])
    make_admin()
    mine, theirs = make_product("Mine", owner=d1), make_product("Theirs", owner=d2)
    h = admin_login("d1@example.com")
    assert create_sale(client, h, [theirs.id]).status_code == 403
    sale = create_sale(client, h, [mine.id]).get_json()["sales"][0]
    assert [s["productName"] for s in client.get("/api/admin/sales", headers=h).get_json()["sales"]] == ["Mine"]
    assert client.get("/api/admin/sales", headers=admin_login("d2@example.com")).get_json()["sales"] == []
    assert client.post(f"/api/admin/sales/{sale['id']}/end", headers=admin_login("d2@example.com")).status_code == 403
    # Without the products permission a distributor cannot touch sales at all.
    make_admin("d3@example.com", "Distributor", ["orders"])
    assert client.get("/api/admin/sales", headers=admin_login("d3@example.com")).status_code == 403


def test_customers_and_visitors_cannot_manage_sales(client, make_product, make_user, user_login):
    p = make_product()
    assert client.post("/api/admin/sales", json={}).status_code == 401
    make_user()
    h = user_login("customer@example.com")
    assert client.post("/api/admin/sales", headers=h, json={"productIds": [p.id], "percent": 50, "startDate": day(0), "endDate": day(0)}).status_code == 403
