# tests/test_auth.py
def test_register_short_password(client):
    r = client.post("/auth/register", json={
        "first_name": "A", "last_name": "B",
        "username": "shortpass",
        "password": "123"
    })
    assert r.status_code in (400, 422)  # schema -> 422; extra guard -> 400

def test_register_and_login_ok(client):
    # register
    r = client.post("/auth/register", json={
        "first_name": "A", "last_name": "B",
        "username": "farida",
        "password": "StrongPass1"
    })
    assert r.status_code == 200

    # login
    r = client.post("/auth/login", data={"username": "farida", "password": "StrongPass1"})
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_me_requires_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
