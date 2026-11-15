import pytest

from app.extensions import db
from app.models import PhLocation, User, UserAddress
from app.services import locations




@pytest.fixture(autouse=True)
def ph_reference(app):
    locations.load_reference()


def place(name, level):
    return PhLocation.query.filter_by(name=name, level=level).first()


def addr_body(**extra):
    base = {
        "label": "Home", "regionCode": place("National Capital Region (NCR)", "Reg").code,
        "cityCode": place("City of Parañaque", "City").code,
        "street": "Dr. A. Santos Ave", "houseNumber": "12",
    }
    base.update(extra)
    return base


def parañaque_barangay():
    city = place("City of Parañaque", "City")
    return PhLocation.query.filter_by(parent_code=city.code, level="Bgy").order_by(PhLocation.name).first()


def test_regions_and_their_children_are_listed(client, make_user):
    make_user()
    regions = client.get("/api/addresses/locations").get_json()["places"]
    assert any(r["name"].startswith("National Capital Region") for r in regions)
    ncr = place("National Capital Region (NCR)", "Reg")
    names = [p["name"] for p in client.get(f"/api/addresses/locations?parent={ncr.code}").get_json()["places"]]
    assert "City of Parañaque" in names and "Quezon City" in names


def test_a_barangay_must_belong_to_the_chosen_city(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    qc = place("Quezon City", "City")
    merville = place("Merville", "Bgy")
    body = addr_body(cityCode=qc.code, barangayCode=merville.code)
    r = client.post("/api/addresses", headers=h, json=body)
    assert r.status_code == 400 and "does not belong" in r.get_json()["error"]


def test_a_matching_barangay_is_accepted(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    b = parañaque_barangay()
    r = client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code))
    assert r.status_code == 201
    assert r.get_json()["address"]["barangay"]["name"] == b.name


def test_no_zip_is_invented_when_none_is_on_file(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    b = parañaque_barangay()
    assert b.zip_code is None
    r = client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code))
    assert r.get_json()["address"]["zipCode"] is None
    z = client.get(f"/api/addresses/locations/{b.code}/zip").get_json()
    assert z == {"code": b.code, "zipCode": None, "available": False}


def test_a_typed_zip_must_be_four_digits(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    b = parañaque_barangay()
    assert client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, zipCode="12")).status_code == 400
    assert client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, zipCode="1700")).status_code == 201


def test_a_mapped_zip_cannot_be_replaced_by_a_different_one(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    b = parañaque_barangay()
    b.zip_code = "1700"
    db.session.commit()
    assert client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, zipCode="1234")).status_code == 400
    r = client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code))
    assert r.get_json()["address"]["zipCode"] == "1700"
    b.zip_code = None
    db.session.commit()


def test_several_addresses_and_one_default_that_the_account_uses(client, make_user, user_login):
    user = make_user()
    h = user_login("customer@example.com")
    b = parañaque_barangay()
    first = client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, label="Home", street="Rizal St")).get_json()["address"]
    second = client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, label="Work", street="Office Ave")).get_json()["address"]
    assert first["isDefault"] is True and second["isDefault"] is False
    client.post(f"/api/addresses/{second['id']}/default", headers=h)
    db.session.refresh(user)
    assert user.address_city == "City of Parañaque" and "Office Ave" in user.address_line1
    listed = client.get("/api/addresses", headers=h).get_json()["addresses"]
    assert len(listed) == 2 and listed[0]["id"] == second["id"]


def test_deleting_the_default_promotes_another(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    b = parañaque_barangay()
    a = client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, street="One St")).get_json()["address"]
    client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, street="Two St"))
    client.delete(f"/api/addresses/{a['id']}", headers=h)
    remaining = client.get("/api/addresses", headers=h).get_json()["addresses"]
    assert len(remaining) == 1 and remaining[0]["isDefault"] is True


def test_another_customer_cannot_change_an_address(client, make_user, user_login):
    make_user()
    make_user("other@example.com", "Other Person")
    b = parañaque_barangay()
    owner = user_login("customer@example.com")
    a = client.post("/api/addresses", headers=owner, json=addr_body(barangayCode=b.code)).get_json()["address"]
    intruder = user_login("other@example.com")
    assert client.put(f"/api/addresses/{a['id']}", headers=intruder, json=addr_body(barangayCode=b.code)).status_code == 404
    assert client.delete(f"/api/addresses/{a['id']}", headers=intruder).status_code == 404


def test_a_street_is_required(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    b = parañaque_barangay()
    assert client.post("/api/addresses", headers=h, json=addr_body(barangayCode=b.code, street="")).status_code == 400
