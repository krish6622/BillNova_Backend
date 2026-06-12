"""Tenant isolation: one tenant must never see or touch another's data."""

from tests.conftest import auth_headers, register


def test_user_list_is_tenant_scoped_and_cross_access_404(client):
    # Tenant A
    a = register(client).json()
    a_token = a["access_token"]
    client.post(
        "/api/users", headers=auth_headers(a_token),
        json={"name": "Asha", "email": "asha@a.in", "password": "cashierpass1"},
    )
    a_users = client.get("/api/users", headers=auth_headers(a_token)).json()
    a_cashier_id = next(u["id"] for u in a_users if u["email"] == "asha@a.in")

    # Tenant B (different business + email)
    b = register(client, business_name="Fancy Store", email="meena@b.in").json()
    b_token = b["access_token"]

    # B sees only its own users
    b_users = client.get("/api/users", headers=auth_headers(b_token)).json()
    b_emails = {u["email"] for u in b_users}
    assert b_emails == {"meena@b.in"}
    assert "asha@a.in" not in b_emails

    # B cannot touch A's user — looks like "not found", not "forbidden"
    patch = client.patch(
        f"/api/users/{a_cashier_id}", headers=auth_headers(b_token), json={"name": "Hacked"}
    )
    assert patch.status_code == 404
    reset = client.post(
        f"/api/users/{a_cashier_id}/reset-password",
        headers=auth_headers(b_token), json={"password": "newpass123"},
    )
    assert reset.status_code == 404
