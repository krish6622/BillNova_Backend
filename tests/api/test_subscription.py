"""Subscription / usage read tests."""

from tests.conftest import auth_headers, register


def test_trial_subscription_summary(client):
    token = register(client).json()["access_token"]
    resp = client.get("/api/subscription", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "Trial"
    assert body["monthly_bill_limit"] == 50  # trial quota default
    assert body["usage"]["bills_count"] == 0
    assert body["usage"]["percent"] == 0.0
    assert body["warning"] is None


def test_plans_listed(client):
    token = register(client).json()["access_token"]
    resp = client.get("/api/subscription/plans", headers=auth_headers(token))
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert names == {"Starter", "Standard", "Professional"}
    limits = {p["name"]: p["monthly_bill_limit"] for p in resp.json()}
    assert limits == {"Starter": 500, "Standard": 2000, "Professional": 5000}
