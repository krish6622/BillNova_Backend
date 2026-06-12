"""Auth flow API tests: register, login, me, refresh, logout."""

from tests.conftest import auth_headers, register


def test_register_creates_tenant_and_owner(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["role"] == "OWNER"
    assert body["tenant"]["subscription_status"] == "Trial"


def test_register_duplicate_email_conflicts(client):
    register(client)
    resp = register(client)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE_RESOURCE"


def test_login_success_and_me(client):
    register(client)
    resp = client.post("/api/auth/login", json={"email": "ravi@shop.in", "password": "supersecret1"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "ravi@shop.in"
    assert me.json()["tenant"]["business_name"] == "Sri Textiles"


def test_login_wrong_password_unauthorized(client):
    register(client)
    resp = client.post("/api/auth/login", json={"email": "ravi@shop.in", "password": "nope"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_protected_endpoint_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_refresh_then_logout_invalidates_refresh(client):
    reg = register(client).json()
    refresh_token = reg["refresh_token"]

    # refresh works before logout
    r1 = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r1.status_code == 200
    assert r1.json()["access_token"]

    # logout bumps token_version
    out = client.post("/api/auth/logout", headers=auth_headers(reg["access_token"]))
    assert out.status_code == 204

    # old refresh token no longer valid
    r2 = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 401
