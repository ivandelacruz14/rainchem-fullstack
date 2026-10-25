import os
import re
import sys
from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Admin, Order, OrderItem, OrderStatusHistory, Product, User  # noqa: E402
from config import TestConfig  # noqa: E402

PASSWORD = "Passw0rd!x"


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_admin(app):
    def _make(email="head@example.com", role="Head Admin", permissions=None, active=True, name="Admin"):
        admin = Admin(
            name=name, email=email, role=role, permissions=permissions, is_active=active,
            password_hash=generate_password_hash(PASSWORD),
        )
        db.session.add(admin)
        db.session.commit()
        return admin
    return _make


@pytest.fixture()
def admin_login(client):
    def _login(email):
        response = client.post("/api/admin/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.get_json()
        return auth(response.get_json()["token"])
    return _login


@pytest.fixture()
def make_user(app):
    def _make(email="customer@example.com", name="Maria Santos"):
        user = User(
            name=name, email=email, verified=True, phone="09171234567",
            password_hash=generate_password_hash(PASSWORD),
        )
        db.session.add(user)
        db.session.commit()
        return user
    return _make


@pytest.fixture()
def user_login(client):
    def _login(email):
        response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.get_json()
        return auth(response.get_json()["token"])
    return _login


@pytest.fixture()
def make_product(app):
    def _make(name="RAIMOL Oil", price=500, stock=50, category="Oils & Fluids", owner=None):
        product = Product(
            name=name, category=category, price=price, stock=stock, short_desc="short",
            description="long", specs=[], benefits=[], usage_steps=[],
            owner_admin_id=owner.id if owner else None,
        )
        db.session.add(product)
        db.session.commit()
        return product
    return _make


@pytest.fixture()
def make_order(app):
    """Creates an order directly in the database with a chosen status and date."""
    counter = {"n": 0}

    def _make(user, lines, status="delivered", created_at=None, payment_status="paid",
              return_status="none", shipping=0):
        counter["n"] += 1
        subtotal = sum(float(unit) * qty for _, unit, qty in lines)
        order = Order(
            order_number=f"ORD-T-{counter['n']:04d}", user_id=user.id, status=status,
            tracking_number=f"RC-TRK-{counter['n']:05d}",
            customer_name=user.name, customer_phone="09171234567", customer_email=user.email,
            address_line1="1 St", address_city="Quezon City", address_province="Metro Manila",
            address_region="NCR", address_zip="1100", payment_method="Cash on Delivery",
            payment_status=payment_status, return_status=return_status,
            subtotal=subtotal, shipping_fee=shipping, total=subtotal + shipping,
            created_at=created_at or datetime.utcnow(),
        )
        db.session.add(order)
        db.session.flush()
        for product, unit, qty in lines:
            db.session.add(OrderItem(
                order_id=order.id, product_id=product.id, product_name=product.name,
                unit_price=unit, discount_rate=0, quantity=qty,
            ))
        db.session.add(OrderStatusHistory(order_id=order.id, status=status))
        db.session.commit()
        return order
    return _make


def days_ago(n, hour=12):
    """A UTC timestamp that falls on the shop's local day `n` days ago (UTC+8)."""
    local_today = (datetime.utcnow() + timedelta(hours=8)).date()
    local = datetime.combine(local_today - timedelta(days=n), datetime.min.time()) + timedelta(hours=hour)
    return local - timedelta(hours=8)


@pytest.fixture()
def mailbox(monkeypatch):
    """Captures the emails the approval flow sends instead of calling Mailjet."""
    sent = []

    def fake_send(to_email, subject, body, **kwargs):
        sent.append({"to": to_email, "subject": subject, "body": body, "kwargs": kwargs})
        return True

    monkeypatch.setattr("app.services.change_requests.send_email", fake_send)
    return sent


def emailed_code(mailbox):
    for mail in reversed(mailbox):
        found = re.search(r"approval code is (\d{6})", mail["body"])
        if found:
            return found.group(1)
    raise AssertionError("no approval code was emailed")


@pytest.fixture()
def approve(client, mailbox):
    """Runs the full approval: password, emailed code, confirm."""
    def _approve(head_headers, request_id):
        started = client.post(f"/api/admin/approvals/{request_id}/approve/start", headers=head_headers, json={"password": PASSWORD})
        assert started.status_code == 200, started.get_json()
        return client.post(f"/api/admin/approvals/{request_id}/approve/confirm", headers=head_headers, json={"code": emailed_code(mailbox)})
    return _approve
