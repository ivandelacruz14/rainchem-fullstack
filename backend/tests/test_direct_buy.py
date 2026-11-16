from app.extensions import db
from app.models import CartItem, Order
from conftest import PASSWORD

COD = "Cash on Delivery"
CUSTOMER = {"name": "Maria Santos", "phone": "09171234567", "email": "customer@example.com"}
ADDRESS = {"line1": "1 Rizal St", "city": "Quezon City", "province": "Metro Manila", "region": "NCR", "zip": "1100"}


def order(client, h, product, qty, direct):
    body = {"items": [{"productId": product.id, "qty": qty}], "customer": CUSTOMER, "address": ADDRESS,
            "paymentMethod": COD, "direct": direct}
    return client.post("/api/orders", headers=h, json=body)


def test_buy_now_leaves_the_same_item_in_the_cart(client, make_user, user_login, make_product):
    user = make_user()
    p = make_product("RAIMOL Oil", price=100, stock=50)
    db.session.add(CartItem(user_id=user.id, product_id=p.id, quantity=5))
    db.session.commit()
    h = user_login("customer@example.com")
    assert order(client, h, p, 5, direct=True).status_code == 201
    row = CartItem.query.filter_by(user_id=user.id, product_id=p.id).first()
    assert row is not None and row.quantity == 5                  # the cart still has its 5 pieces
    assert Order.query.count() == 1


def test_a_cart_checkout_still_clears_what_it_ordered(client, make_user, user_login, make_product):
    user = make_user()
    p = make_product("RAIMOL Oil", price=100, stock=50)
    db.session.add(CartItem(user_id=user.id, product_id=p.id, quantity=5))
    db.session.commit()
    h = user_login("customer@example.com")
    assert order(client, h, p, 5, direct=False).status_code == 201
    assert CartItem.query.filter_by(user_id=user.id, product_id=p.id).first() is None
