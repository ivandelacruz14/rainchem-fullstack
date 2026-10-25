def test_visitors_can_browse(client, make_product):
    p = make_product()
    assert client.get("/api/products").status_code == 200
    assert client.get(f"/api/products/{p.id}").status_code == 200
    assert client.get(f"/api/products/{p.id}/reviews").status_code == 200
    assert client.get("/api/services").status_code == 200


def test_visitors_cannot_use_protected_actions(client, make_product):
    p = make_product()
    for method, url in [
        ("get", "/api/cart"), ("post", "/api/cart/items"), ("post", "/api/orders"), ("get", "/api/orders"),
        ("post", "/api/orders/1/reviews"), ("post", "/api/services/bookings"), ("get", "/api/orders/track/RC-TRK-1"),
        ("get", "/api/auth/me"), ("post", f"/api/products"), ("get", "/api/admin/orders"),
    ]:
        assert getattr(client, method)(url, json={}).status_code == 401, url


def test_public_products_do_not_leak_internal_fields(client, make_product):
    make_product()
    product = client.get("/api/products").get_json()["products"][0]
    assert "ownerId" not in product


def test_tracking_only_for_the_owner(client, make_user, make_product, make_order, user_login):
    owner, other = make_user(), make_user("o@example.com", "Other One")
    order = make_order(owner, [(make_product(), 100, 1)], status="shipped")
    assert client.get(f"/api/orders/track/{order.tracking_number}", headers=user_login(owner.email)).status_code == 200
    assert client.get(f"/api/orders/track/{order.tracking_number}", headers=user_login(other.email)).status_code == 404


def test_cors_origin_list_ignores_trailing_slash():
    from app import frontend_origins
    assert frontend_origins("https://a.app/, https://b.app") == ["https://a.app", "https://b.app"]
