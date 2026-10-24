import sys
import types
import unittest
from datetime import datetime, timedelta
from unittest import mock

try:
    import sklearn  # noqa: F401
except ImportError:  # only when scikit-learn is not installed in the test environment
    for name in ("sklearn", "sklearn.feature_extraction", "sklearn.feature_extraction.text",
                 "sklearn.metrics", "sklearn.metrics.pairwise"):
        sys.modules[name] = types.ModuleType(name)
    sys.modules["sklearn.feature_extraction.text"].TfidfVectorizer = object
    sys.modules["sklearn.metrics.pairwise"].cosine_similarity = lambda *a, **k: None

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Admin, Order, OrderItem, OrderStatusHistory, PasswordReset, Product,
    ProductReview, Service, ServiceArea, User,
)
from app.models.admin import ROLE_DISTRIBUTOR, ROLE_HEAD_ADMIN
from config import TestConfig


class Config(TestConfig):
    TESTING = True
    SALES_UTC_OFFSET_HOURS = 8


HEAD_PASSWORD = "Head123!x"
USER_PASSWORD = "Rider123!x"


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(Config)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

        self.head = Admin(name="Head", email="head@example.com", role=ROLE_HEAD_ADMIN,
                          password_hash=generate_password_hash(HEAD_PASSWORD))
        self.legacy = Admin(name="Legacy", email="legacy@example.com", role="Super Admin",
                            password_hash=generate_password_hash(HEAD_PASSWORD))
        self.dist = Admin(name="Dist", email="dist@example.com", role=ROLE_DISTRIBUTOR,
                          permissions=["manage_products", "view_sales"],
                          password_hash=generate_password_hash(HEAD_PASSWORD))
        self.bare = Admin(name="Bare", email="bare@example.com", role=ROLE_DISTRIBUTOR,
                          permissions=[], password_hash=generate_password_hash(HEAD_PASSWORD))
        self.user = User(name="Rica Santos", email="rica@example.com", phone="09171234567",
                         verified=True, password_hash=generate_password_hash(USER_PASSWORD))
        self.other = User(name="Other Person", email="other@example.com", phone="09170000000",
                          verified=True, password_hash=generate_password_hash(USER_PASSWORD))
        db.session.add_all([self.head, self.legacy, self.dist, self.bare, self.user, self.other])
        db.session.commit()

        self.head_product = self.make_product("Head Oil", 100, owner=None)
        self.dist_product = self.make_product("Dist Oil", 200, owner=self.dist.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def make_product(self, name, price, owner=None, stock=50):
        product = Product(name=name, category="Oils & Fluids", price=price, stock=stock,
                          short_desc="s", description="d", owner_admin_id=owner)
        db.session.add(product)
        db.session.commit()
        return product

    def admin_headers(self, email="head@example.com"):
        res = self.client.post("/api/admin/auth/login", json={"email": email, "password": HEAD_PASSWORD})
        self.assertEqual(res.status_code, 200, res.get_json())
        return {"Authorization": f"Bearer {res.get_json()['token']}"}

    def user_headers(self, email="rica@example.com"):
        res = self.client.post("/api/auth/login", json={"email": email, "password": USER_PASSWORD})
        self.assertEqual(res.status_code, 200, res.get_json())
        return {"Authorization": f"Bearer {res.get_json()['token']}"}

    def make_order(self, user, lines, status="delivered", created_at=None, return_status="none"):
        order = Order(
            order_number=f"RC-{Order.query.count() + 1:05d}", user_id=user.id, status=status,
            tracking_number="TRK", customer_name=user.name, customer_phone="09171234567",
            customer_email=user.email, address_line1="a", address_city="Quezon City",
            address_province="Metro Manila", address_region="NCR", address_zip="1100",
            payment_method="Cash on Delivery", subtotal=0, shipping_fee=0, total=0,
            return_status=return_status, created_at=created_at or datetime.utcnow(),
        )
        db.session.add(order)
        db.session.flush()
        total = 0
        for product, qty, unit_price in lines:
            db.session.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name,
                                     unit_price=unit_price, discount_rate=0, quantity=qty))
            total += qty * unit_price
        order.subtotal = total
        order.total = total
        db.session.add(OrderStatusHistory(order_id=order.id, status=status))
        db.session.commit()
        return order


class AccessControlTests(BaseCase):
    def test_distributor_without_permission_is_blocked(self):
        headers = self.admin_headers("bare@example.com")
        res = self.client.post("/api/products", json={"name": "X", "price": 10, "stock": 1}, headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_distributor_creates_and_owns_product_but_not_others(self):
        headers = self.admin_headers("dist@example.com")
        created = self.client.post("/api/products", json={
            "name": "Mine", "price": 50, "stock": 5, "shortDesc": "s", "description": "d"}, headers=headers)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.get_json()["product"]["ownerAdminId"], self.dist.id)

        res = self.client.put(f"/api/products/{self.head_product.id}", json={"price": 1}, headers=headers)
        self.assertEqual(res.status_code, 403)
        res = self.client.delete(f"/api/products/{self.head_product.id}", headers=headers)
        self.assertEqual(res.status_code, 403)

        listing = self.client.get("/api/products/manage", headers=headers).get_json()["products"]
        self.assertEqual({p["name"] for p in listing}, {"Dist Oil", "Mine"})

    def test_distributor_cannot_reach_head_only_endpoints(self):
        headers = self.admin_headers("dist@example.com")
        for method, url in [
            ("get", "/api/admin/auth/accounts"), ("get", "/api/admin/users"),
            ("get", "/api/admin/overview"), ("get", "/api/admin/knowledge"),
            ("get", "/api/admin/settings/payment"), ("get", "/api/admin/chat-monitor"),
        ]:
            res = getattr(self.client, method)(url, headers=headers)
            self.assertEqual(res.status_code, 403, url)

    def test_distributor_cannot_change_order_status(self):
        order = self.make_order(self.user, [(self.dist_product, 1, 200)], status="shipped")
        headers = self.admin_headers("dist@example.com")
        res = self.client.post(f"/api/admin/orders/{order.id}/status", json={"status": "delivered"}, headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_and_customer_tokens_are_rejected_on_admin_routes(self):
        self.assertEqual(self.client.get("/api/admin/analytics/report").status_code, 401)
        res = self.client.get("/api/admin/analytics/report", headers=self.user_headers())
        self.assertEqual(res.status_code, 403)

    def test_legacy_admin_roles_keep_full_access(self):
        headers = self.admin_headers("legacy@example.com")
        self.assertEqual(self.client.get("/api/admin/auth/accounts", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/admin/overview", headers=headers).status_code, 200)

    def test_distributor_order_view_hides_customer_details_and_other_products(self):
        self.dist.permissions = ["view_orders"]
        db.session.commit()
        self.make_order(self.user, [(self.dist_product, 2, 200), (self.head_product, 1, 100)])
        headers = self.admin_headers("dist@example.com")
        orders = self.client.get("/api/admin/orders", headers=headers).get_json()["orders"]
        self.assertEqual(len(orders), 1)
        self.assertEqual([i["name"] for i in orders[0]["items"]], ["Dist Oil"])
        self.assertEqual(orders[0]["customer"]["email"], "")
        self.assertNotIn("paymentMethod", orders[0])

    def test_distributor_without_view_orders_permission_blocked(self):
        res = self.client.get("/api/admin/orders", headers=self.admin_headers("dist@example.com"))
        self.assertEqual(res.status_code, 403)


class AccountManagementTests(BaseCase):
    def test_create_requires_acting_password(self):
        headers = self.admin_headers()
        body = {"name": "New", "email": "new@example.com", "role": "Distributor", "password": "Newpass1!",
                "permissions": ["manage_products", "bogus"]}
        self.assertEqual(self.client.post("/api/admin/auth/accounts", json=body, headers=headers).status_code, 403)
        body["currentPassword"] = HEAD_PASSWORD
        res = self.client.post("/api/admin/auth/accounts", json=body, headers=headers)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["admin"]["permissions"], ["manage_products"])

    def test_cannot_demote_self_or_remove_last_head(self):
        headers = self.admin_headers()
        res = self.client.put(f"/api/admin/auth/accounts/{self.head.id}",
                              json={"role": "Distributor", "currentPassword": HEAD_PASSWORD}, headers=headers)
        self.assertEqual(res.status_code, 400)
        res = self.client.delete(f"/api/admin/auth/accounts/{self.head.id}",
                                 json={"currentPassword": HEAD_PASSWORD}, headers=headers)
        self.assertEqual(res.status_code, 400)

    def test_head_can_update_distributor_permissions_and_disable(self):
        headers = self.admin_headers()
        res = self.client.put(f"/api/admin/auth/accounts/{self.dist.id}", headers=headers, json={
            "permissions": ["view_orders"], "currentPassword": HEAD_PASSWORD})
        self.assertEqual(res.get_json()["admin"]["permissions"], ["view_orders"])
        self.client.put(f"/api/admin/auth/accounts/{self.dist.id}", headers=headers,
                        json={"isActive": False, "currentPassword": HEAD_PASSWORD})
        res = self.client.post("/api/admin/auth/login", json={"email": "dist@example.com", "password": HEAD_PASSWORD})
        self.assertEqual(res.status_code, 403)

    def test_disabled_admin_token_stops_working(self):
        headers = self.admin_headers("dist@example.com")
        self.dist.is_active = False
        db.session.commit()
        self.assertEqual(self.client.get("/api/products/manage", headers=headers).status_code, 403)

    def test_distributor_cannot_edit_own_permissions(self):
        headers = self.admin_headers("dist@example.com")
        res = self.client.put(f"/api/admin/auth/accounts/{self.dist.id}", headers=headers, json={
            "permissions": ["view_orders", "manage_services"], "currentPassword": HEAD_PASSWORD})
        self.assertEqual(res.status_code, 403)


class ReviewTests(BaseCase):
    def test_public_summary_is_empty_without_records(self):
        res = self.client.get(f"/api/products/{self.head_product.id}/reviews").get_json()
        self.assertEqual(res["summary"]["count"], 0)
        self.assertIsNone(res["summary"]["average"])
        product = self.client.get(f"/api/products/{self.head_product.id}").get_json()["product"]
        self.assertIsNone(product["rating"])
        self.assertEqual(product["reviews"], 0)

    def test_requires_login_and_delivered_purchase(self):
        url = f"/api/products/{self.head_product.id}/reviews"
        self.assertEqual(self.client.post(url, json={"rating": 5}).status_code, 401)
        headers = self.user_headers()
        self.assertEqual(self.client.post(url, json={"rating": 5}, headers=headers).status_code, 403)
        self.make_order(self.user, [(self.head_product, 1, 100)], status="shipped")
        self.assertEqual(self.client.post(url, json={"rating": 5}, headers=headers).status_code, 403)

    def test_other_customers_delivery_does_not_make_me_eligible(self):
        self.make_order(self.other, [(self.head_product, 1, 100)])
        res = self.client.post(f"/api/products/{self.head_product.id}/reviews",
                               json={"rating": 5, "userId": self.other.id}, headers=self.user_headers())
        self.assertEqual(res.status_code, 403)

    def test_eligible_review_duplicate_and_aggregates(self):
        order = self.make_order(self.user, [(self.head_product, 1, 100)])
        headers = self.user_headers()
        url = f"/api/products/{self.head_product.id}/reviews"
        self.assertTrue(self.client.get(url + "/eligibility", headers=headers).get_json()["canReview"])

        self.assertEqual(self.client.post(url, json={"rating": 0}, headers=headers).status_code, 400)
        self.assertEqual(self.client.post(url, json={"rating": 6}, headers=headers).status_code, 400)
        self.assertEqual(self.client.post(url, json={"rating": 4, "comment": "x" * 501}, headers=headers).status_code, 400)

        res = self.client.post(url, json={"rating": 4, "comment": "Works well", "orderId": 999}, headers=headers)
        self.assertEqual(res.status_code, 201)
        review = ProductReview.query.one()
        self.assertEqual((review.order_id, review.user_id), (order.id, self.user.id))
        self.assertEqual(res.get_json()["review"]["reviewer"], "Rica S.")

        self.assertEqual(self.client.post(url, json={"rating": 5}, headers=headers).status_code, 409)

        self.make_order(self.other, [(self.head_product, 1, 100)])
        self.client.post(url, json={"rating": 5}, headers=self.user_headers("other@example.com"))
        summary = self.client.get(url).get_json()["summary"]
        self.assertEqual((summary["count"], summary["average"]), (2, 4.5))
        product = self.client.get(f"/api/products/{self.head_product.id}").get_json()["product"]
        self.assertEqual((product["rating"], product["reviews"]), (4.5, 2))

    def test_order_level_review_creates_product_reviews(self):
        order = self.make_order(self.user, [(self.head_product, 1, 100), (self.dist_product, 1, 200)])
        res = self.client.post(f"/api/orders/{order.id}/review", json={"rating": 5, "comment": "Great"},
                               headers=self.user_headers())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ProductReview.query.count(), 2)
        res = self.client.post(f"/api/products/{self.head_product.id}/reviews", json={"rating": 3},
                               headers=self.user_headers())
        self.assertEqual(res.status_code, 409)


class MigrationTests(BaseCase):
    def test_backfill_copies_existing_order_reviews_once(self):
        from sqlalchemy import text
        from app.services.schema_updates import BACKFILL_PRODUCT_REVIEWS
        order = self.make_order(self.user, [(self.head_product, 1, 100), (self.dist_product, 1, 200)])
        order.review_rating = 4
        order.review_comment = "Good"
        unreviewed = self.make_order(self.other, [(self.head_product, 1, 100)])
        db.session.commit()
        for _ in range(2):
            db.session.execute(text(BACKFILL_PRODUCT_REVIEWS))
            db.session.commit()
        rows = ProductReview.query.all()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.order_id == order.id and r.rating == 4 for r in rows))
        self.assertNotIn(unreviewed.id, {r.order_id for r in rows})


class ServiceTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.admin = self.admin_headers()
        res = self.client.post("/api/admin/services", headers=self.admin, json={
            "name": "Oil change", "description": "Labor and disposal", "category": "Maintenance"})
        self.service_id = res.get_json()["service"]["id"]
        for name, price, available in [("Quezon City", 150, True), ("Batangas", 320, True), ("Cebu", 500, False)]:
            r = self.client.post(f"/api/admin/services/{self.service_id}/areas", headers=self.admin,
                                 json={"areaName": name, "price": price, "isAvailable": available})
            self.assertEqual(r.status_code, 201)

    def areas(self):
        service = self.client.get("/api/services").get_json()["services"][0]
        return {a["areaName"]: a for a in service["areas"]}

    def test_public_listing_shows_location_specific_prices_and_availability(self):
        areas = self.areas()
        self.assertEqual(areas["Quezon City"]["price"], 150.0)
        self.assertEqual(areas["Batangas"]["price"], 320.0)
        self.assertFalse(areas["Cebu"]["isAvailable"])

    def test_booking_requires_login_and_uses_database_price(self):
        url = f"/api/services/{self.service_id}/bookings"
        payload = {"areaId": self.areas()["Batangas"]["id"], "name": "Rica", "phone": "09171234567",
                   "address": "1 Main St", "price": 1}
        self.assertEqual(self.client.post(url, json=payload).status_code, 401)
        res = self.client.post(url, json=payload, headers=self.user_headers())
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["booking"]["price"], 320.0)

    def test_unavailable_area_cannot_be_booked(self):
        res = self.client.post(f"/api/services/{self.service_id}/bookings", headers=self.user_headers(), json={
            "areaId": self.areas()["Cebu"]["id"], "name": "Rica", "phone": "09171234567", "address": "x"})
        self.assertEqual(res.status_code, 400)

    def test_area_of_another_service_is_rejected(self):
        other = Service(name="Other", description="d")
        db.session.add(other)
        db.session.flush()
        foreign = ServiceArea(service_id=other.id, area_name="Elsewhere", price=10)
        db.session.add(foreign)
        db.session.commit()
        res = self.client.post(f"/api/services/{self.service_id}/bookings", headers=self.user_headers(), json={
            "areaId": foreign.id, "name": "Rica", "phone": "09171234567", "address": "x"})
        self.assertEqual(res.status_code, 400)

    def test_disabled_service_keeps_history_and_blocks_new_bookings(self):
        area = self.areas()["Quezon City"]
        url = f"/api/services/{self.service_id}/bookings"
        payload = {"areaId": area["id"], "name": "Rica", "phone": "09171234567", "address": "x"}
        self.assertEqual(self.client.post(url, json=payload, headers=self.user_headers()).status_code, 201)
        self.client.put(f"/api/admin/services/{self.service_id}", headers=self.admin, json={"isActive": False})
        self.assertEqual(self.client.post(url, json=payload, headers=self.user_headers()).status_code, 400)
        self.assertEqual(len(self.client.get("/api/admin/services/bookings", headers=self.admin).get_json()["bookings"]), 1)
        res = self.client.delete(f"/api/admin/services/{self.service_id}/areas/{area['id']}", headers=self.admin)
        self.assertEqual(res.status_code, 409)

    def test_distributor_service_scope(self):
        self.dist.permissions = ["manage_services"]
        db.session.commit()
        headers = self.admin_headers("dist@example.com")
        res = self.client.put(f"/api/admin/services/{self.service_id}", headers=headers, json={"name": "Hijack"})
        self.assertEqual(res.status_code, 403)
        mine = self.client.post("/api/admin/services", headers=headers,
                                json={"name": "Mine", "description": "d"}).get_json()["service"]
        res = self.client.post(f"/api/admin/services/{mine['id']}/areas", headers=headers,
                               json={"areaName": "Makati", "price": 99})
        self.assertEqual(res.status_code, 201)
        listing = self.client.get("/api/admin/services", headers=headers).get_json()["services"]
        self.assertEqual([s["name"] for s in listing], ["Mine"])

    def test_negative_price_rejected(self):
        res = self.client.post(f"/api/admin/services/{self.service_id}/areas", headers=self.admin,
                               json={"areaName": "Davao", "price": -5})
        self.assertEqual(res.status_code, 400)


class PasswordResetTests(BaseCase):
    def request_token(self):
        with mock.patch("app.routes.auth.send_email") as sender:
            res = self.client.post("/api/auth/forgot-password", json={"email": "rica@example.com"})
            self.assertEqual(res.status_code, 200)
            body = sender.call_args[0][2]
        link = [w for w in body.split() if "/reset-password?token=" in w][0]
        return link

    def test_link_uses_configured_frontend_url_and_stores_only_a_hash(self):
        self.app.config["FRONTEND_URL"] = "https://rainchem.vercel.app"
        link = self.request_token()
        self.assertTrue(link.startswith("https://rainchem.vercel.app/reset-password?token="))
        token = link.split("token=")[1]
        self.assertNotEqual(PasswordReset.query.one().token, token)

    def test_unknown_email_gives_same_response_and_sends_nothing(self):
        with mock.patch("app.routes.auth.send_email") as sender:
            res = self.client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
        self.assertEqual(res.status_code, 200)
        sender.assert_not_called()

    def test_full_flow_single_use(self):
        token = self.request_token().split("token=")[1]
        self.assertTrue(self.client.get(f"/api/auth/reset-password/validate?token={token}").get_json()["valid"])

        weak = self.client.post("/api/auth/reset-password", json={"token": token, "password": "weak"})
        self.assertEqual(weak.status_code, 400)

        with mock.patch("app.routes.auth.send_email"):
            ok = self.client.post("/api/auth/reset-password", json={"token": token, "password": "Brandnew1!"})
        self.assertEqual(ok.status_code, 200)
        login = self.client.post("/api/auth/login", json={"email": "rica@example.com", "password": "Brandnew1!"})
        self.assertEqual(login.status_code, 200)

        again = self.client.post("/api/auth/reset-password", json={"token": token, "password": "Another1!x"})
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.get_json()["reason"], "used")

    def test_expired_and_invalid_tokens(self):
        token = self.request_token().split("token=")[1]
        PasswordReset.query.update({"expires_at": datetime.utcnow() - timedelta(minutes=1)})
        db.session.commit()
        res = self.client.post("/api/auth/reset-password", json={"token": token, "password": "Brandnew1!"})
        self.assertEqual(res.get_json()["reason"], "expired")
        res = self.client.post("/api/auth/reset-password", json={"token": "nope", "password": "Brandnew1!"})
        self.assertEqual(res.get_json()["reason"], "invalid")
        self.assertEqual(self.client.get("/api/auth/reset-password/validate?token=").status_code, 400)

    def test_new_request_invalidates_old_link(self):
        first = self.request_token().split("token=")[1]
        PasswordReset.query.update({"created_at": datetime.utcnow() - timedelta(minutes=5)})
        db.session.commit()
        self.request_token()
        res = self.client.post("/api/auth/reset-password", json={"token": first, "password": "Brandnew1!"})
        self.assertEqual(res.get_json()["reason"], "used")


class PublicAccessTests(BaseCase):
    def test_catalog_and_services_are_public(self):
        self.assertEqual(self.client.get("/api/products").status_code, 200)
        self.assertEqual(self.client.get(f"/api/products/{self.head_product.id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/products/{self.head_product.id}/reviews").status_code, 200)
        self.assertEqual(self.client.get("/api/services").status_code, 200)

    def test_protected_actions_need_a_customer_token(self):
        body = {"items": [{"productId": self.head_product.id, "qty": 1}]}
        self.assertEqual(self.client.post("/api/orders", json=body).status_code, 401)
        self.assertEqual(self.client.get("/api/orders").status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/admin/analytics/report", headers=self.user_headers()).status_code, 403)

    def test_orders_are_not_visible_across_customers(self):
        order = self.make_order(self.user, [(self.head_product, 1, 100)])
        res = self.client.get(f"/api/orders/{order.id}", headers=self.user_headers("other@example.com"))
        self.assertEqual(res.status_code, 404)


class AnalyticsTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.today = (datetime.utcnow() + timedelta(hours=8)).date()
        noon_local = datetime.combine(self.today, datetime.min.time()) + timedelta(hours=4)  # 12:00 +08:00 as UTC 04:00
        self.noon_utc = noon_local

    def report(self, headers=None, **params):
        res = self.client.get("/api/admin/analytics/report", query_string=params, headers=headers or self.admin_headers())
        self.assertEqual(res.status_code, 200, res.get_json())
        return res.get_json()

    def test_totals_use_unit_price_once_and_exclude_unconfirmed_and_cancelled(self):
        self.make_order(self.user, [(self.head_product, 3, 90)], created_at=self.noon_utc)
        self.make_order(self.user, [(self.dist_product, 1, 200)], status="shipped", created_at=self.noon_utc)
        self.make_order(self.user, [(self.head_product, 9, 100)], status="cancelled", created_at=self.noon_utc)
        self.make_order(self.user, [(self.head_product, 9, 100)], status="pending_confirmation", created_at=self.noon_utc)
        self.make_order(self.user, [(self.head_product, 9, 100)], return_status="approved", created_at=self.noon_utc)
        data = self.report(granularity="daily")
        self.assertEqual(data["summary"]["revenue"], 470.0)
        self.assertEqual(data["summary"]["unitsSold"], 4)
        self.assertEqual(data["summary"]["orders"], 2)
        self.assertEqual(data["series"][-1]["revenue"], 470.0)
        self.assertEqual(len(data["series"]), 30)
        names = {p["name"]: p for p in data["products"]}
        self.assertEqual(names["Head Oil"]["units"], 3)
        self.assertEqual(data["bestSeller"]["name"], "Head Oil")
        self.assertEqual(data["lowestSeller"]["name"], "Dist Oil")

    def test_local_midnight_boundary(self):
        local_midnight_utc = datetime.combine(self.today, datetime.min.time()) - timedelta(hours=8)
        self.make_order(self.user, [(self.head_product, 1, 100)], created_at=local_midnight_utc + timedelta(minutes=5))
        self.make_order(self.user, [(self.head_product, 1, 100)], created_at=local_midnight_utc - timedelta(minutes=5))
        data = self.report(granularity="daily", start=self.today.isoformat(), end=self.today.isoformat())
        self.assertEqual(data["summary"]["orders"], 1)

    def test_comparison_with_previous_period(self):
        prev_day = self.noon_utc - timedelta(days=1)
        self.make_order(self.user, [(self.head_product, 1, 100)], created_at=prev_day)
        self.make_order(self.user, [(self.head_product, 3, 100)], created_at=self.noon_utc)
        data = self.report(granularity="daily", start=self.today.isoformat(), end=self.today.isoformat())
        self.assertEqual(data["summary"]["revenue"], 300.0)
        self.assertEqual(data["previousSummary"]["revenue"], 100.0)
        self.assertEqual(data["change"]["revenue"], 200.0)

    def test_weekly_and_monthly_buckets(self):
        self.make_order(self.user, [(self.head_product, 2, 100)], created_at=self.noon_utc)
        weekly = self.report(granularity="weekly")
        self.assertEqual(len(weekly["series"]), 12)
        self.assertEqual(weekly["series"][-1]["revenue"], 200.0)
        monthly = self.report(granularity="monthly")
        self.assertEqual(len(monthly["series"]), 12)
        self.assertEqual(monthly["series"][-1]["revenue"], 200.0)

    def test_no_data_returns_zeros_not_invented_figures(self):
        data = self.report()
        self.assertEqual(data["summary"], {"revenue": 0.0, "unitsSold": 0, "orders": 0, "averageOrderValue": 0.0})
        self.assertIsNone(data["bestSeller"])
        self.assertTrue(all(not p["sufficientData"] for p in data["forecast"]["products"]))
        self.assertEqual(data["forecast"]["expectedRevenue"], 0.0)
        self.assertTrue(data["forecast"]["isEstimate"])

    def test_forecast_needs_history_then_estimates_and_flags_restock(self):
        self.head_product.stock = 2
        db.session.commit()
        this_week = self.today - timedelta(days=self.today.weekday())
        for weeks_back in range(1, 7):
            when = datetime.combine(this_week - timedelta(weeks=weeks_back) + timedelta(days=2), datetime.min.time()) + timedelta(hours=4)
            self.make_order(self.user, [(self.head_product, 2, 100)], created_at=when)
        data = self.report()
        row = next(p for p in data["forecast"]["products"] if p["productId"] == self.head_product.id)
        self.assertTrue(row["sufficientData"])
        self.assertEqual(row["expectedUnits"], 8)
        self.assertTrue(row["needsRestock"])
        self.assertEqual(row["confidence"], "moderate")
        self.assertEqual(data["forecast"]["expectedRevenue"], 800.0)

    def test_recommendations_reference_recorded_figures(self):
        self.head_product.stock = 3
        db.session.commit()
        for _ in range(2):
            self.make_order(self.user, [(self.head_product, 5, 100)], created_at=self.noon_utc)
        data = self.report()
        types = {(r["type"], r["name"]) for r in data["recommendations"]}
        self.assertIn(("prioritize", "Head Oil"), types)
        self.assertIn(("restock", "Head Oil"), types)
        self.assertIn(("promote", "Dist Oil"), types)

    def test_distributor_sees_only_own_products_and_needs_permission(self):
        self.make_order(self.user, [(self.head_product, 1, 100), (self.dist_product, 2, 200)], created_at=self.noon_utc)
        data = self.report(headers=self.admin_headers("dist@example.com"))
        self.assertEqual(data["summary"]["revenue"], 400.0)
        self.assertEqual([p["name"] for p in data["products"]], ["Dist Oil"])
        res = self.client.get("/api/admin/analytics/report", headers=self.admin_headers("bare@example.com"))
        self.assertEqual(res.status_code, 403)

    def test_product_history_scope_and_validation(self):
        self.make_order(self.user, [(self.dist_product, 2, 200)], created_at=self.noon_utc)
        head = self.admin_headers()
        res = self.client.get(f"/api/admin/analytics/products/{self.dist_product.id}/history", headers=head)
        self.assertEqual(res.get_json()["summary"]["revenue"], 400.0)
        dist = self.admin_headers("dist@example.com")
        self.assertEqual(self.client.get(f"/api/admin/analytics/products/{self.head_product.id}/history", headers=dist).status_code, 404)
        bad = self.client.get("/api/admin/analytics/report?start=2026-02-01&end=2026-01-01", headers=head)
        self.assertEqual(bad.status_code, 400)
        bad = self.client.get("/api/admin/analytics/report?granularity=hourly", headers=head)
        self.assertEqual(bad.status_code, 400)


if __name__ == "__main__":
    unittest.main()
