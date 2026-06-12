"""User management + RBAC tests."""

from tests.conftest import auth_headers, register


def _owner_token(client):
    return register(client).json()["access_token"]


def test_owner_can_create_cashier(client):
    token = _owner_token(client)
    resp = client.post(
        "/api/users",
        headers=auth_headers(token),
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1", "role": "CASHIER"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "CASHIER"

    users = client.get("/api/users", headers=auth_headers(token))
    assert users.status_code == 200
    emails = {u["email"] for u in users.json()}
    assert {"ravi@shop.in", "asha@shop.in"} <= emails


def test_duplicate_email_on_create_conflicts(client):
    token = _owner_token(client)
    client.post(
        "/api/users", headers=auth_headers(token),
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    resp = client.post(
        "/api/users", headers=auth_headers(token),
        json={"name": "Asha2", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    assert resp.status_code == 409


def test_cashier_cannot_manage_users(client):
    owner = _owner_token(client)
    client.post(
        "/api/users", headers=auth_headers(owner),
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    cashier = client.post(
        "/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"}
    ).json()["access_token"]

    # cashier blocked from owner-only user management
    assert client.get("/api/users", headers=auth_headers(cashier)).status_code == 403
    create = client.post(
        "/api/users", headers=auth_headers(cashier),
        json={"name": "X", "email": "x@shop.in", "password": "password12"},
    )
    assert create.status_code == 403
    assert create.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_deactivated_user_cannot_login(client):
    owner = _owner_token(client)
    cashier = client.post(
        "/api/users", headers=auth_headers(owner),
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    ).json()
    # deactivate
    patch = client.patch(
        f"/api/users/{cashier['id']}", headers=auth_headers(owner), json={"is_active": False}
    )
    assert patch.status_code == 200
    login = client.post("/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"})
    assert login.status_code == 401
