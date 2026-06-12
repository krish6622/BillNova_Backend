"""Security posture tests: auth required, no secret leakage, admin gating."""

from tests.conftest import auth_headers, register

PROTECTED_GETS = [
    "/api/auth/me",
    "/api/products",
    "/api/sales",
    "/api/dashboard",
    "/api/subscription",
    "/api/users",
    "/api/settings",
    "/api/inventory/stock",
    "/api/purchases",
    "/api/reports/inventory/stock",
]


def test_protected_endpoints_require_auth(client):
    for path in PROTECTED_GETS:
        assert client.get(path).status_code == 401, f"{path} should require auth"


def test_password_hash_never_leaks(client):
    reg = register(client)
    assert "password_hash" not in reg.text
    headers = auth_headers(reg.json()["access_token"])

    me = client.get("/api/auth/me", headers=headers)
    assert "password_hash" not in me.text

    client.post(
        "/api/users", headers=headers,
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    users = client.get("/api/users", headers=headers)
    assert "password_hash" not in users.text
    assert "cashierpass1" not in users.text


def test_activate_disabled_without_admin_key(client):
    reg = register(client).json()
    # Default config has no admin key -> activation is fully disabled.
    resp = client.post(
        "/api/subscription/activate",
        json={"tenant_id": reg["tenant"]["id"], "status": "Active"},
    )
    assert resp.status_code == 403
