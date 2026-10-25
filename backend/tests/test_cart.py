def test_cart_requires_login(client):
    assert client.get("/api/cart").status_code == 401
    assert client.post("/api/cart/items", json={"productId": 1}).status_code == 401


def test_cart_is_private_per_customer(client, make_user, make_product, user_login):
    p = make_product(price=100)
    make_user()
    make_user("b@example.com", "Bea Cruz")
    a, b = user_login("customer@example.com"), user_login("b@example.com")
    assert client.post("/api/cart/items", headers=a, json={"productId": p.id, "qty": 3}).status_code == 200
    assert client.get("/api/cart", headers=b).get_json()["items"] == []
    assert client.put(f"/api/cart/items/{p.id}", headers=b, json={"qty": 9}).status_code == 404
    assert client.get("/api/cart", headers=a).get_json()["items"][0]["qty"] == 3


def test_totals_use_server_prices_and_rules(client, make_user, make_product, user_login):
    p = make_product(price=100)
    make_user()
    h = user_login("customer@example.com")
    cart = client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 10}).get_json()
    s = cart["summary"]
    assert s["subtotal"] == 900.0  # 10% bulk discount at 10 units
    assert s["shipping"] == 0.0 and s["total"] == 900.0 and s["savings"] == 100.0
    p.price = 200
    from app.extensions import db
    db.session.commit()
    assert client.get("/api/cart", headers=h).get_json()["summary"]["subtotal"] == 1800.0


def test_quantity_limits(client, make_user, make_product, user_login):
    p = make_product(stock=5)
    out = make_product("Empty", stock=0)
    make_user()
    h = user_login("customer@example.com")
    assert client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 6}).status_code == 400
    assert client.post("/api/cart/items", headers=h, json={"productId": out.id}).status_code == 400
    assert client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 0}).status_code == 400
    client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 5})
    assert client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 1}).status_code == 400
    assert client.put(f"/api/cart/items/{p.id}", headers=h, json={"qty": 0}).get_json()["items"] == []


def test_checkout_uses_saved_cart_and_clears_it(client, make_user, make_product, user_login):
    p = make_product(price=100, stock=10)
    make_user()
    h = user_login("customer@example.com")
    client.post("/api/cart/items", headers=h, json={"productId": p.id, "qty": 2})
    order = client.post("/api/orders", headers=h, json={
        "customer": {"name": "M", "phone": "09171234567", "email": "customer@example.com"},
        "address": {"line1": "a", "city": "b", "province": "c", "region": "d", "zip": "1"},
        "paymentMethod": "Cash on Delivery",
    })
    assert order.status_code == 201
    assert order.get_json()["order"]["subtotal"] == 200.0
    assert client.get("/api/cart", headers=h).get_json()["items"] == []
