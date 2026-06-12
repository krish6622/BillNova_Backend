"""Dashboard KPIs — composed from the report/subscription/inventory services."""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.services import inventory_service, report_service, subscription_service


def kpis(db: Session, tenant_id: uuid.UUID, *, today: date | None = None) -> dict:
    today = today or date.today()
    day = report_service.daily_sales(db, tenant_id, today)["summary"]
    month = report_service.monthly_sales(db, tenant_id, today.year, today.month)["summary"]
    sub = subscription_service.get_subscription_summary(db, tenant_id)
    low = inventory_service.low_stock(db, tenant_id)

    return {
        "today_sales": {"amount": day["gross"], "count": day["bills"]},
        "monthly_sales": {"amount": month["gross"], "count": month["bills"]},
        "bills_this_month": month["bills"],
        "subscription": {
            "plan": sub["plan"],
            "limit": sub["monthly_bill_limit"],
            "used": sub["usage"]["bills_count"],
            "percent": sub["usage"]["percent"],
        },
        "low_stock_count": len(low),
    }
