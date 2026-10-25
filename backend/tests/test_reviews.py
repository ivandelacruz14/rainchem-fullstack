from app.extensions import db


def setup_order(make_user, make_product, make_order, status="delivered", lines=1):
    user = make_user()
    products = [make_product(f"Product {i}", price=100) for i in range(lines)]
    order = make_order(user, [(p, 100, 2) for p in products], status=status)
    return user, products, order


def test_cannot_review_before_delivery(client, make_user, make_product, make_order, user_login):
    user, (product,), order = setup_order(make_user, make_product, make_order, status="shipped")
    h = user_login(user.email)
    r = client.post(f"/api/orders/{order.id}/reviews", headers=h, json={"reviews": [{"productId": product.id, "rating": 5}]})
    assert r.status_code == 400
    assert client.get(f"/api/products/{product.id}/reviews").get_json()["summary"]["count"] == 0


def test_review_flow_and_computed_rating(client, make_user, make_product, make_order, user_login):
    user, (a, b), order = setup_order(make_user, make_product, make_order, lines=2)
    h = user_login(user.email)
    assert client.get("/api/orders", headers=h).get_json()["orders"][0]["tab"] == "to_review"

    ok = client.post(f"/api/orders/{order.id}/reviews", headers=h, json={"reviews": [
        {"productId": a.id, "rating": 4, "comment": " Smooth engine "}]})
    assert ok.status_code == 200
    assert ok.get_json()["order"]["canReview"] is True  # product b still waiting

    data = client.get(f"/api/products/{a.id}/reviews").get_json()
    assert data["summary"] == {"average": 4.0, "count": 1, "distribution": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 0}}
    assert data["reviews"][0]["comment"] == "Smooth engine"
    assert data["reviews"][0]["author"] == "Maria S."
    assert "email" not in str(data)

    listing = client.get("/api/products").get_json()["products"]
    by_name = {p["name"]: p for p in listing}
    assert by_name["Product 0"]["rating"] == 4.0 and by_name["Product 0"]["reviews"] == 1
    assert by_name["Product 1"]["rating"] == 0 and by_name["Product 1"]["reviews"] == 0

    dup = client.post(f"/api/orders/{order.id}/reviews", headers=h, json={"reviews": [{"productId": a.id, "rating": 1}]})
    assert dup.status_code == 400
    client.post(f"/api/orders/{order.id}/reviews", headers=h, json={"reviews": [{"productId": b.id, "rating": 5}]})
    assert client.get("/api/orders", headers=h).get_json()["orders"][0]["tab"] == "completed"


def test_validation(client, make_user, make_product, make_order, user_login):
    user, (p,), order = setup_order(make_user, make_product, make_order)
    h = user_login(user.email)
    url = f"/api/orders/{order.id}/reviews"
    for entry in ({"productId": p.id, "rating": 0}, {"productId": p.id, "rating": 6}, {"productId": p.id, "rating": "x"},
                  {"productId": p.id, "rating": 5, "comment": "a" * 501}, {"rating": 5}):
        assert client.post(url, headers=h, json={"reviews": [entry]}).status_code == 400, entry
    assert client.post(url, headers=h, json={"reviews": []}).status_code == 400


def test_cannot_review_other_peoples_orders_or_foreign_products(client, make_user, make_product, make_order, user_login):
    user, (p,), order = setup_order(make_user, make_product, make_order)
    other = make_user("other@example.com", "Other Person")
    stranger = user_login(other.email)
    assert client.post(f"/api/orders/{order.id}/reviews", headers=stranger, json={"reviews": [{"productId": p.id, "rating": 5}]}).status_code == 404
    not_in_order = make_product("Not bought")
    h = user_login(user.email)
    assert client.post(f"/api/orders/{order.id}/reviews", headers=h, json={"reviews": [{"productId": not_in_order.id, "rating": 5}]}).status_code == 400


def test_reviews_require_login_and_no_returns(client, make_user, make_product, make_order, user_login):
    user, (p,), order = setup_order(make_user, make_product, make_order)
    assert client.post(f"/api/orders/{order.id}/reviews", json={"reviews": []}).status_code == 401
    order.return_status = "requested"
    db.session.commit()
    h = user_login(user.email)
    assert client.post(f"/api/orders/{order.id}/reviews", headers=h, json={"reviews": [{"productId": p.id, "rating": 5}]}).status_code == 400


def test_legacy_order_level_endpoint_still_works(client, make_user, make_product, make_order, user_login):
    user, (p,), order = setup_order(make_user, make_product, make_order)
    h = user_login(user.email)
    assert client.post(f"/api/orders/{order.id}/review", headers=h, json={"rating": 5, "comment": "great"}).status_code == 200
    assert client.get(f"/api/products/{p.id}/reviews").get_json()["summary"]["count"] == 1


def test_reviews_of_orders_no_longer_delivered_are_hidden(client, make_user, make_product, make_order, user_login):
    user, (p,), order = setup_order(make_user, make_product, make_order)
    client.post(f"/api/orders/{order.id}/review", headers=user_login(user.email), json={"rating": 5})
    order.status = "cancelled"
    db.session.commit()
    assert client.get(f"/api/products/{p.id}/reviews").get_json()["summary"]["count"] == 0


def test_legacy_review_backfill_only_for_single_product_orders(app, make_user, make_product, make_order):
    from app.models import ProductReview
    from app.services.schema_updates import backfill_single_product_reviews
    user = make_user()
    a, b = make_product("A"), make_product("B")
    single = make_order(user, [(a, 100, 1)])
    multi = make_order(user, [(a, 100, 1), (b, 100, 1)])
    for o in (single, multi):
        o.review_rating, o.review_comment = 4, "ok"
    db.session.commit()
    backfill_single_product_reviews(db, app.logger)
    backfill_single_product_reviews(db, app.logger)  # idempotent
    rows = ProductReview.query.all()
    assert len(rows) == 1 and rows[0].order_id == single.id
