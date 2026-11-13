from app.extensions import db
from app.models import Order, User
from conftest import PASSWORD

COD = "Cash on Delivery"
CUSTOMER = {"name": "Maria Santos", "phone": "09171234567", "email": "customer@example.com"}
ADDRESS = {"line1": "1 Rizal St", "city": "Quezon City", "province": "Metro Manila", "region": "NCR", "zip": "1100"}


def place(client, h, product, qty, method=COD, **extra):
    body = {"items": [{"productId": product.id, "qty": qty}], "customer": CUSTOMER, "address": ADDRESS, "paymentMethod": method, **extra}
    return client.post("/api/orders", headers=h, json=body)


def boxed(make_product, name="RAIMOL Oil", pack=24):
    p = make_product(name, price=100, stock=10000)
    p.pack_size = pack
    db.session.commit()
    return p


def business(verified=False):
    user = User.query.filter_by(email="customer@example.com").first()
    user.account_type, user.business_name, user.business_verified = "business", "Juan Hardware", verified
    db.session.commit()


def online(monkeypatch):
    monkeypatch.setattr("app.services.payment_flow.available_methods", lambda: [COD, "GCash"])


def test_a_personal_order_of_a_few_pieces_is_unchanged(client, make_user, user_login, make_product):
    make_user()
    p = boxed(make_product)
    r = place(client, user_login("customer@example.com"), p, 2)
    assert r.status_code == 201
    order = Order.query.one()
    assert order.bulk_boxes == 1 and order.is_bulk is False


def test_a_business_basic_account_is_limited_in_boxes(client, make_user, user_login, make_product):
    user = make_user()
    business(verified=False)
    p = boxed(make_product)
    h = user_login("customer@example.com")
    r = place(client, h, p, 21 * 24)                       # 21 boxes of 24
    assert r.status_code == 400 and "20 boxes" in r.get_json()["error"]
    assert place(client, h, p, 20 * 24).status_code == 201  # exactly the limit


def test_a_product_without_pack_size_counts_one_piece_per_box(client, make_user, user_login, make_product):
    make_user()
    business(verified=False)
    p = make_product("Single bottle", price=100, stock=500)
    r = place(client, user_login("customer@example.com"), p, 21)
    assert r.status_code == 400 and "20 boxes" in r.get_json()["error"]


def test_bulk_orders_must_be_prepaid_and_are_marked(client, make_user, user_login, make_product, monkeypatch):
    make_user()
    p = boxed(make_product)
    h = user_login("customer@example.com")
    assert place(client, h, p, 100 * 24).status_code == 400                       # 100 boxes on cash on delivery
    online(monkeypatch)
    r = place(client, h, p, 100 * 24, method="GCash")
    assert r.status_code == 201
    order = Order.query.one()
    assert order.is_bulk is True and order.bulk_boxes == 100


def test_a_verified_business_gets_the_higher_limit_and_still_prepays(client, make_user, user_login, make_product, monkeypatch):
    make_user()
    business(verified=True)
    p = boxed(make_product)
    h = user_login("customer@example.com")
    online(monkeypatch)
    assert place(client, h, p, 150 * 24, method="GCash").status_code == 201
    assert place(client, h, p, 150 * 24).status_code == 400                       # same order on cash is refused
    assert place(client, h, p, 201 * 24, method="GCash").status_code == 400      # over the verified limit


def test_the_same_order_twice_asks_for_confirmation(client, make_user, user_login, make_product):
    make_user()
    p = boxed(make_product)
    h = user_login("customer@example.com")
    assert place(client, h, p, 2).status_code == 201
    again = place(client, h, p, 2)
    assert again.status_code == 409
    body = again.get_json()
    assert body["needsConfirmation"] is True and body["duplicateOrder"]
    assert place(client, h, p, 2, confirmDuplicate=True).status_code == 201
    assert Order.query.count() == 2


def test_a_different_order_is_not_a_duplicate(client, make_user, user_login, make_product):
    make_user()
    p = boxed(make_product)
    h = user_login("customer@example.com")
    assert place(client, h, p, 2).status_code == 201
    assert place(client, h, p, 3).status_code == 201


def test_registration_remembers_the_account_type(client, make_user):
    make_user()
    client.post("/api/auth/register", json={"name": "Juan", "email": "juan@example.com", "phone": "09171234567",
                                             "password": PASSWORD, "accountType": "business", "businessName": "Juan Hardware"})
    u = User.query.filter_by(email="juan@example.com").first()
    assert u.account_type == "business" and u.business_name == "Juan Hardware" and u.business_verified is False


def test_a_business_signup_needs_a_business_name(client, make_user):
    make_user()
    r = client.post("/api/auth/register", json={"name": "Juan", "email": "juan2@example.com", "phone": "09171234567",
                                                 "password": PASSWORD, "accountType": "business"})
    assert r.status_code == 400 and "Enter your business name" in str(r.get_json())


def test_a_personal_signup_is_the_default(client, make_user):
    make_user()
    client.post("/api/auth/register", json={"name": "Ana", "email": "ana@example.com", "phone": "09171234567", "password": PASSWORD})
    assert User.query.filter_by(email="ana@example.com").first().account_type == "personal"


def test_admin_can_set_pieces_per_box(client, make_admin, admin_login, make_product):
    make_admin()
    h = admin_login("head@example.com")
    p = make_product("Set Box", price=100, stock=10)
    r = client.put(f"/api/products/{p.id}", headers=h, json={"packSize": 24})
    assert r.status_code == 200
    db.session.refresh(p)
    assert p.pack_size == 24
    assert client.put(f"/api/products/{p.id}", headers=h, json={"packSize": 0.5}).status_code == 400
