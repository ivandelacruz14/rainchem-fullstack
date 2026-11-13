from datetime import datetime

from app.extensions import db
from app.models import CartItem, Order, Product, User
from conftest import PASSWORD


def google_style_user(email="gaccount@example.com"):
    user = User(name="Google Person", email=email, google_id="g-123", verified=True)
    db.session.add(user)
    db.session.commit()
    return user


def test_a_new_registration_already_chose_its_type(client, make_user):
    make_user()
    client.post("/api/auth/register", json={"name": "Ana", "email": "ana@example.com", "phone": "09171234567", "password": PASSWORD})
    assert User.query.filter_by(email="ana@example.com").first().account_type_chosen is True


def test_an_older_or_google_account_has_not_chosen_yet(client):
    user = google_style_user()
    assert user.account_type_chosen is False


def test_choosing_business_needs_a_name_and_is_saved(client, make_user, user_login):
    make_user()
    google_style_user()
    h = user_login("customer@example.com")
    assert client.put("/api/auth/me/account-type", headers=h, json={"accountType": "business"}).status_code == 400
    r = client.put("/api/auth/me/account-type", headers=h, json={"accountType": "business", "businessName": "Juan Hardware", "tin": ""})
    assert r.status_code == 200
    u = r.get_json()["user"]
    assert u["accountType"] == "business" and u["businessName"] == "Juan Hardware" and u["accountTypeChosen"] is True
    assert u["tin"] is None


def test_switching_type_clears_the_business_verification(client, make_user, user_login):
    user = make_user()
    user.account_type, user.business_name, user.business_verified = "business", "Juan Hardware", True
    db.session.commit()
    h = user_login("customer@example.com")
    r = client.put("/api/auth/me/account-type", headers=h, json={"accountType": "personal"})
    assert r.get_json()["user"]["businessVerified"] is False


def test_delete_needs_the_right_password(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    assert client.delete("/api/auth/me/account", headers=h, json={"password": "wrong"}).status_code == 400
    assert User.query.filter_by(email="customer@example.com").first() is not None


def test_delete_erases_the_person_but_keeps_the_order_history(client, make_user, user_login, make_product, make_order):
    user = make_user()
    p = make_product("Oil", price=100, stock=50)
    order = make_order(user, [(p, 100, 1)], status="delivered", payment_status="paid")
    db.session.add(CartItem(user_id=user.id, product_id=p.id, quantity=2))
    db.session.commit()
    h = user_login("customer@example.com")
    r = client.delete("/api/auth/me/account", headers=h, json={"password": PASSWORD})
    assert r.status_code == 200
    db.session.refresh(user)
    assert user.email.endswith("@deleted.invalid") and user.password_hash is None and user.name == "Deleted user"
    assert user.deleted_at is not None and CartItem.query.filter_by(user_id=user.id).count() == 0
    assert Order.query.filter_by(id=order.id).first() is not None                  # kept for accounting
    assert client.post("/api/auth/login", json={"email": "customer@example.com", "password": PASSWORD}).status_code == 401


def test_a_google_only_account_must_type_delete(client, user_login, make_user):
    google = google_style_user()
    from app.utils.auth_decorators import create_user_token
    token = create_user_token(google)
    h = {"Authorization": f"Bearer {token}"}
    assert client.delete("/api/auth/me/account", headers=h, json={"confirmText": "yes"}).status_code == 400
    assert client.delete("/api/auth/me/account", headers=h, json={"confirmText": "delete"}).status_code == 200
