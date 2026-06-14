"""Dashboard KPIs — composed from the report/subscription/inventory services."""

import calendar
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sale import STATUS_VOID, Sale
from app.services import inventory_service, report_service, subscription_service


def kpis(db: Session, tenant_id: uuid.UUID, *, today: date | None = None) -> dict:
    today = today or date.today()
    monthly = report_service.monthly_sales(db, tenant_id, today.year, today.month)
    day = report_service.daily_sales(db, tenant_id, today)["summary"]
    month = monthly["summary"]
    sub = subscription_service.get_subscription_summary(db, tenant_id)
    low = inventory_service.low_stock(db, tenant_id)

    # Sales trend — one point per day of the current month (0 for days with no sales).
    by_day = {d["date"]: d["total"] for d in monthly["days"]}
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    trend = [
        {"date": f"{today.year:04d}-{today.month:02d}-{d:02d}",
         "total": by_day.get(f"{today.year:04d}-{today.month:02d}-{d:02d}", 0.0)}
        for d in range(1, days_in_month + 1)
    ]

    month_start = today.replace(day=1)
    return {
        "scope": "owner",
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
        "trend": trend,
        "top_products": report_service.top_products(db, tenant_id, month_start, today, limit=5),
    }


def cashier_kpis(
    db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID, *, today: date | None = None
) -> dict:
    """Limited dashboard for a cashier: only *their own* billing activity today.

    Deliberately excludes all business analytics (monthly revenue, profit, GST, low
    stock, top products, subscription usage) — a cashier sees just what they billed.
    """
    today = today or date.today()
    own_today = [
        Sale.tenant_id == tenant_id,
        Sale.created_by == user_id,
        Sale.status != STATUS_VOID,
        func.date(Sale.created_at) == today,
    ]
    count = db.scalar(select(func.count(Sale.id)).where(*own_today)) or 0
    collection = db.scalar(select(func.coalesce(func.sum(Sale.grand_total), 0)).where(*own_today)) or 0

    recent = list(
        db.scalars(
            select(Sale)
            .where(Sale.tenant_id == tenant_id, Sale.created_by == user_id)
            .order_by(Sale.created_at.desc())
            .limit(6)
        )
    )
    return {
        "scope": "cashier",
        "today_bills": {"count": int(count), "amount": float(collection)},
        "today_collection": float(collection),
        "bills_generated": int(count),
        "recent_bills": [
            {
                "id": str(s.id),
                "invoice_number": s.invoice_number,
                "created_at": s.created_at.isoformat(),
                "grand_total": float(s.grand_total),
                "status": s.status,
            }
            for s in recent
        ],
    }
