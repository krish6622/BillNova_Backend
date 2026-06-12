"""Subscription / usage read + manual-activation tests."""

import uuid
from datetime import date

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.usage import BillUsage
from tests.conftest import auth_headers, register


def _prev_month(today: date) -> tuple[int, int]:
    return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)


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


def test_activate_requires_admin_key(client, monkeypatch):
    reg = register(client).json()
    tenant_id = reg["tenant"]["id"]
    # No key configured -> disabled.
    monkeypatch.setattr(settings, "admin_api_key", "")
    body = {"tenant_id": tenant_id, "status": "Active"}
    assert client.post("/api/subscription/activate", json=body).status_code == 403
    # Key configured but wrong header -> 403.
    monkeypatch.setattr(settings, "admin_api_key", "secret-key")
    assert client.post(
        "/api/subscription/activate", json=body, headers={"X-Admin-Key": "wrong"}
    ).status_code == 403


def test_activate_upgrades_plan(client, monkeypatch):
    reg = register(client).json()
    tenant_id = reg["tenant"]["id"]
    token = reg["access_token"]
    plans = client.get("/api/subscription/plans", headers=auth_headers(token)).json()
    pro_id = next(p["id"] for p in plans if p["name"] == "Professional")

    monkeypatch.setattr(settings, "admin_api_key", "secret-key")
    resp = client.post(
        "/api/subscription/activate",
        json={"tenant_id": tenant_id, "plan_id": pro_id, "status": "Active",
              "period_start": "2026-06-01", "period_end": "2026-06-30"},
        headers={"X-Admin-Key": "secret-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Active"
    assert resp.json()["monthly_bill_limit"] == 5000

    # Owner now sees the upgraded plan.
    summary = client.get("/api/subscription", headers=auth_headers(token)).json()
    assert summary["plan"] == "Professional"
    assert summary["status"] == "Active"


def test_monthly_usage_resets_each_month(client, engine):
    reg = register(client).json()
    tenant_id = reg["tenant"]["id"]
    token = reg["access_token"]

    # Record heavy usage in the PREVIOUS month.
    py, pm = _prev_month(date.today())
    Session = sessionmaker(bind=engine, future=True)
    s = Session()
    s.add(BillUsage(tenant_id=uuid.UUID(tenant_id), year=py, month=pm, bills_count=49))
    s.commit()
    s.close()

    # Current month's usage is unaffected.
    summary = client.get("/api/subscription", headers=auth_headers(token)).json()
    assert summary["usage"]["bills_count"] == 0
    assert summary["warning"] is None
