"""Report aggregations (Owner-only). Figures here are the single source of truth
shared by both the JSON endpoints and the PDF/Excel exporters."""

import calendar
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sale import Sale, SaleItem

_S = func.coalesce


def _sales_summary(db: Session, tenant_id: uuid.UUID, start: date, end: date) -> dict:
    row = db.execute(
        select(
            func.count(Sale.id),
            _S(func.sum(Sale.grand_total), 0),
            _S(func.sum(Sale.total_taxable), 0),
            _S(func.sum(Sale.total_gst), 0),
            _S(func.sum(Sale.total_discount), 0),
        ).where(
            Sale.tenant_id == tenant_id,
            func.date(Sale.created_at) >= start,
            func.date(Sale.created_at) <= end,
        )
    ).one()
    return {
        "bills": int(row[0]),
        "gross": float(row[1]),
        "taxable": float(row[2]),
        "gst": float(row[3]),
        "discount": float(row[4]),
    }


def daily_sales(db: Session, tenant_id: uuid.UUID, day: date) -> dict:
    return {"date": day.isoformat(), "summary": _sales_summary(db, tenant_id, day, day)}


def monthly_sales(db: Session, tenant_id: uuid.UUID, year: int, month: int) -> dict:
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    summary = _sales_summary(db, tenant_id, start, end)
    day_expr = func.date(Sale.created_at)
    day_rows = db.execute(
        select(day_expr, func.count(Sale.id), _S(func.sum(Sale.grand_total), 0))
        .where(
            Sale.tenant_id == tenant_id,
            day_expr >= start,
            day_expr <= end,
        )
        .group_by(day_expr)
        .order_by(day_expr)
    ).all()
    days = [{"date": str(r[0]), "bills": int(r[1]), "total": float(r[2])} for r in day_rows]
    return {"year": year, "month": month, "summary": summary, "days": days}


def gst_summary(db: Session, tenant_id: uuid.UUID, start: date, end: date) -> dict:
    rows = db.execute(
        select(
            SaleItem.gst_percentage,
            _S(func.sum(SaleItem.taxable_value), 0),
            _S(func.sum(SaleItem.cgst), 0),
            _S(func.sum(SaleItem.sgst), 0),
            _S(func.sum(SaleItem.igst), 0),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            SaleItem.tenant_id == tenant_id,
            func.date(Sale.created_at) >= start,
            func.date(Sale.created_at) <= end,
        )
        .group_by(SaleItem.gst_percentage)
        .order_by(SaleItem.gst_percentage)
    ).all()
    out_rows = [
        {
            "gst_percentage": float(r[0]),
            "taxable": float(r[1]),
            "cgst": float(r[2]),
            "sgst": float(r[3]),
            "igst": float(r[4]),
            "total_gst": float(r[2]) + float(r[3]) + float(r[4]),
        }
        for r in rows
    ]
    return {"from": start.isoformat(), "to": end.isoformat(), "rows": out_rows}


def hsn_summary(db: Session, tenant_id: uuid.UUID, start: date, end: date) -> dict:
    rows = db.execute(
        select(
            _S(SaleItem.hsn_code, "—"),
            _S(func.sum(SaleItem.quantity), 0),
            _S(func.sum(SaleItem.taxable_value), 0),
            _S(func.sum(SaleItem.cgst + SaleItem.sgst + SaleItem.igst), 0),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            SaleItem.tenant_id == tenant_id,
            func.date(Sale.created_at) >= start,
            func.date(Sale.created_at) <= end,
        )
        .group_by(_S(SaleItem.hsn_code, "—"))
        .order_by(_S(SaleItem.hsn_code, "—"))
    ).all()
    out_rows = [
        {"hsn_code": str(r[0]), "quantity": float(r[1]), "taxable": float(r[2]), "gst": float(r[3])}
        for r in rows
    ]
    return {"from": start.isoformat(), "to": end.isoformat(), "rows": out_rows}


def top_products(db: Session, tenant_id: uuid.UUID, start: date, end: date, *, limit: int = 5) -> list[dict]:
    rows = db.execute(
        select(
            SaleItem.product_name,
            _S(func.sum(SaleItem.quantity), 0),
            _S(func.sum(SaleItem.line_total), 0),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            SaleItem.tenant_id == tenant_id,
            func.date(Sale.created_at) >= start,
            func.date(Sale.created_at) <= end,
        )
        .group_by(SaleItem.product_name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(limit)
    ).all()
    return [{"name": r[0], "quantity": float(r[1]), "amount": float(r[2])} for r in rows]


def stock_report(db: Session, tenant_id: uuid.UUID) -> dict:
    products = db.scalars(
        select(Product)
        .where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
        .order_by(Product.name)
    ).all()
    rows = [
        {
            "product_code": p.product_code,
            "name": p.name,
            "unit": p.unit,
            "current_stock": float(p.current_stock),
            "purchase_price": float(p.purchase_price),
            "stock_value": float(p.current_stock) * float(p.purchase_price),
        }
        for p in products
    ]
    total_value = sum(r["stock_value"] for r in rows)
    return {"rows": rows, "total_value": total_value}
