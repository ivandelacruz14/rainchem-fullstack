from conftest import PASSWORD


def test_the_profile_saves_first_middle_and_last_name(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    r = client.put("/api/auth/me/profile", headers=h, json={
        "firstName": "  Maria ", "middleName": "", "lastName": "Santos", "phone": "09171234567", "age": "26", "gender": "Female"})
    assert r.status_code == 200
    me = r.get_json()["user"]
    assert me["firstName"] == "Maria" and me["middleName"] is None and me["lastName"] == "Santos"
    assert me["name"] == "Maria Santos"


def test_the_profile_refuses_a_name_with_numbers(client, make_user, user_login):
    make_user()
    h = user_login("customer@example.com")
    r = client.put("/api/auth/me/profile", headers=h, json={"firstName": "M4ria", "lastName": "Santos", "phone": "09171234567"})
    assert r.status_code == 400
