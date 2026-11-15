import io

from app.models import Admin, Order
from app.extensions import db
from conftest import PASSWORD
from test_delivery_round4 import JPEG, assign, ready_order, riders, scan, upload


def delivered(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    head, rider, other = riders(make_admin, admin_login)
    assign(client, head, order, "rider@example.com")
    client.post(f"/api/rider/{order.id}/start", headers=rider)
    for code in ("RC-OIL-1", "RC-OIL-1", "RC-FIL-1"):
        scan(client, rider, order, code)
    upload(client, rider, order)
    assert client.post(f"/api/rider/{order.id}/deliver", headers=rider).status_code == 200
    return order, head, rider, other


def test_only_active_riders_are_listed(client, make_admin, admin_login):
    make_admin()
    make_admin("rider@example.com", "Rider")
    h = admin_login("head@example.com")
    riders_list = client.get("/api/admin/orders/riders", headers=h).get_json()["riders"]
    rider_id = Admin.query.filter_by(email="rider@example.com").first().id
    assert [r["id"] for r in riders_list] == [rider_id]          # the head admin is not a rider
    assert all(set(r) == {"id", "name"} for r in riders_list)     # no emails or other details


def test_a_rider_cannot_list_riders_or_read_orders_as_admin(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = delivered(client, make_order, make_user, make_product, make_admin, admin_login)
    assert client.get("/api/admin/orders/riders", headers=rider).status_code == 403
    assert client.get("/api/admin/orders", headers=rider).status_code == 403


def test_the_proof_photo_is_shown_to_staff_who_can_see_orders(client, make_order, make_user, make_product, make_admin, admin_login):
    order, head, rider, other = delivered(client, make_order, make_user, make_product, make_admin, admin_login)
    r = client.get(f"/api/admin/orders/{order.id}/delivery-proof", headers=head)
    assert r.status_code == 200 and r.data == JPEG and r.headers["Content-Type"].startswith("image/jpeg")
    assert client.get(f"/api/admin/orders/{order.id}/delivery-proof", headers=rider).status_code == 403


def test_no_proof_means_not_found(client, make_order, make_user, make_product, make_admin, admin_login):
    order, a, b = ready_order(make_order, make_user, make_product)
    make_admin()
    h = admin_login("head@example.com")
    assert client.get(f"/api/admin/orders/{order.id}/delivery-proof", headers=h).status_code == 404
