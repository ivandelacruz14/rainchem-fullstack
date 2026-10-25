from datetime import date, timedelta

PAYLOAD = {
    "name": "Oil Change", "description": "Quick oil change", "category": "Maintenance",
    "requirements": "Bring plate number",
    "areas": [
        {"name": "Quezon City", "price": 150, "isAvailable": True},
        {"name": "Baguio", "price": 400, "isAvailable": True},
        {"name": "Palawan", "price": 900, "isAvailable": False},
    ],
}


def create(client, headers, payload=None):
    r = client.post("/api/admin/services", headers=headers, json=payload or PAYLOAD)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["service"]


def booking_body(service, **extra):
    body = {"serviceId": service["id"], "area": "Quezon City", "name": "Maria Santos", "phone": "09171234567",
            "address": "12 Road, QC"}
    body.update(extra)
    return body


def test_public_sees_area_specific_price_and_availability(client, make_admin, admin_login):
    make_admin()
    service = create(client, admin_login("head@example.com"))
    qc = client.get("/api/services?area=Quezon City").get_json()["services"][0]["selected"]
    assert qc == {"area": "Quezon City", "available": True, "price": 150.0, "reason": None}
    assert client.get("/api/services?area=Baguio").get_json()["services"][0]["selected"]["price"] == 400.0
    assert client.get("/api/services?area=Palawan").get_json()["services"][0]["selected"]["available"] is False
    assert client.get("/api/services?area=Cebu").get_json()["services"][0]["selected"]["available"] is False
    assert client.get("/api/services/areas").get_json()["areas"] == ["Baguio", "Quezon City"]


def test_booking_price_comes_from_the_database_not_the_request(client, make_admin, admin_login, make_user, user_login):
    make_admin()
    service = create(client, admin_login("head@example.com"))
    make_user()
    h = user_login("customer@example.com")
    r = client.post("/api/services/bookings", headers=h, json=booking_body(service, area="Baguio", price=1, total=1))
    assert r.status_code == 201
    assert r.get_json()["booking"]["price"] == 400.0
    assert r.get_json()["booking"]["area"] == "Baguio"


def test_booking_blocked_when_unavailable_or_not_offered_or_inactive(client, make_admin, admin_login, make_user, user_login):
    make_admin()
    ah = admin_login("head@example.com")
    service = create(client, ah)
    make_user()
    h = user_login("customer@example.com")
    assert client.post("/api/services/bookings", headers=h, json=booking_body(service, area="Palawan")).status_code == 400
    assert client.post("/api/services/bookings", headers=h, json=booking_body(service, area="Cebu")).status_code == 400
    client.put(f"/api/admin/services/{service['id']}", headers=ah, json={"isActive": False})
    assert client.post("/api/services/bookings", headers=h, json=booking_body(service)).status_code == 404
    assert client.get("/api/services").get_json()["services"] == []


def test_booking_requires_login_and_valid_input(client, make_admin, admin_login, make_user, user_login):
    make_admin()
    service = create(client, admin_login("head@example.com"))
    assert client.post("/api/services/bookings", json=booking_body(service)).status_code == 401
    make_user()
    h = user_login("customer@example.com")
    assert client.post("/api/services/bookings", headers=h, json=booking_body(service, phone="x")).status_code == 400
    assert client.post("/api/services/bookings", headers=h, json=booking_body(service, address="")).status_code == 400
    yesterday = (date.today() - timedelta(days=3)).isoformat()
    assert client.post("/api/services/bookings", headers=h, json=booking_body(service, preferredDate=yesterday)).status_code == 400


def test_disabling_keeps_history_and_blocks_delete(client, make_admin, admin_login, make_user, user_login):
    make_admin()
    ah = admin_login("head@example.com")
    service = create(client, ah)
    make_user()
    h = user_login("customer@example.com")
    client.post("/api/services/bookings", headers=h, json=booking_body(service))
    assert client.delete(f"/api/admin/services/{service['id']}", headers=ah).status_code == 409
    # Removing an area that has bookings only switches it off.
    kept = [a for a in service["areas"] if a["name"] != "Quezon City"]
    updated = client.put(f"/api/admin/services/{service['id']}", headers=ah, json={"areas": kept}).get_json()["service"]
    qc = next(a for a in updated["areas"] if a["name"] == "Quezon City")
    assert qc["available"] is False
    assert len(client.get("/api/services/bookings", headers=h).get_json()["bookings"]) == 1


def test_area_validation(client, make_admin, admin_login):
    make_admin()
    ah = admin_login("head@example.com")
    bad_price = {**PAYLOAD, "areas": [{"name": "QC", "price": -1}]}
    dup = {**PAYLOAD, "areas": [{"name": "QC", "price": 1}, {"name": "qc", "price": 2}]}
    for body in (bad_price, dup, {**PAYLOAD, "name": ""}):
        assert client.post("/api/admin/services", headers=ah, json=body).status_code == 400


def test_distributor_scope(client, make_admin, admin_login):
    make_admin()
    make_admin("d1@example.com", "Distributor", ["services"])
    make_admin("d2@example.com", "Distributor", ["services"])
    h1, h2 = admin_login("d1@example.com"), admin_login("d2@example.com")
    s1 = create(client, h1)
    assert client.put(f"/api/admin/services/{s1['id']}", headers=h2, json={"name": "Hijack"}).status_code == 403
    assert client.get("/api/admin/services", headers=h2).get_json()["services"] == []
    assert len(client.get("/api/admin/services", headers=h1).get_json()["services"]) == 1


def test_booking_status_flow_and_customer_cancel(client, make_admin, admin_login, make_user, user_login):
    make_admin()
    ah = admin_login("head@example.com")
    service = create(client, ah)
    make_user()
    h = user_login("customer@example.com")
    b = client.post("/api/services/bookings", headers=h, json=booking_body(service)).get_json()["booking"]
    url = f"/api/admin/services/bookings/{b['id']}/status"
    assert client.post(url, headers=ah, json={"status": "completed"}).status_code == 400
    assert client.post(url, headers=ah, json={"status": "confirmed"}).status_code == 200
    assert client.post(f"/api/services/bookings/{b['id']}/cancel", headers=h).status_code == 400
    assert client.post(url, headers=ah, json={"status": "completed"}).status_code == 200
