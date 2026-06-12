"""Reports router (Owner-only): sales, GST, HSN, stock — JSON + PDF/Excel export."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import DbSession, TenantId, require_owner
from app.core.errors import AppError
from app.services import export_service, report_service

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_owner)])


def _month_start(today: date) -> date:
    return today.replace(day=1)


@router.get("/sales/daily")
def sales_daily(db: DbSession, tenant_id: TenantId, day: date = Query(default_factory=date.today, alias="date")):
    return report_service.daily_sales(db, tenant_id, day)


@router.get("/sales/monthly")
def sales_monthly(
    db: DbSession,
    tenant_id: TenantId,
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
):
    return report_service.monthly_sales(db, tenant_id, year, month)


@router.get("/gst/summary")
def gst_summary(
    db: DbSession,
    tenant_id: TenantId,
    from_date: date = Query(default_factory=lambda: _month_start(date.today())),
    to_date: date = Query(default_factory=date.today),
):
    return report_service.gst_summary(db, tenant_id, from_date, to_date)


@router.get("/gst/hsn")
def gst_hsn(
    db: DbSession,
    tenant_id: TenantId,
    from_date: date = Query(default_factory=lambda: _month_start(date.today())),
    to_date: date = Query(default_factory=date.today),
):
    return report_service.hsn_summary(db, tenant_id, from_date, to_date)


@router.get("/inventory/stock")
def inventory_stock(db: DbSession, tenant_id: TenantId):
    return report_service.stock_report(db, tenant_id)


def _build_table(db, tenant_id, report: str, *, day, year, month, from_date, to_date):
    """Return (filename, title, columns, rows) for a report — shared by exporters."""
    if report == "sales-daily":
        s = report_service.daily_sales(db, tenant_id, day)["summary"]
        return (
            f"daily-sales-{day}",
            f"Daily Sales — {day}",
            ["Metric", "Value"],
            [["Bills", s["bills"]], ["Gross", s["gross"]], ["Taxable", s["taxable"]],
             ["GST", s["gst"]], ["Discount", s["discount"]]],
        )
    if report == "sales-monthly":
        rep = report_service.monthly_sales(db, tenant_id, year, month)
        rows = [[d["date"], d["bills"], d["total"]] for d in rep["days"]]
        rows.append(["TOTAL", rep["summary"]["bills"], rep["summary"]["gross"]])
        return (f"monthly-sales-{year}-{month:02d}", f"Monthly Sales — {year}-{month:02d}",
                ["Date", "Bills", "Total"], rows)
    if report == "gst-summary":
        rep = report_service.gst_summary(db, tenant_id, from_date, to_date)
        rows = [[r["gst_percentage"], r["taxable"], r["cgst"], r["sgst"], r["igst"], r["total_gst"]]
                for r in rep["rows"]]
        return (f"gst-summary-{from_date}-{to_date}", f"GST Summary — {from_date} to {to_date}",
                ["GST %", "Taxable", "CGST", "SGST", "IGST", "Total GST"], rows)
    if report == "hsn-summary":
        rep = report_service.hsn_summary(db, tenant_id, from_date, to_date)
        rows = [[r["hsn_code"], r["quantity"], r["taxable"], r["gst"]] for r in rep["rows"]]
        return (f"hsn-summary-{from_date}-{to_date}", f"HSN Summary — {from_date} to {to_date}",
                ["HSN", "Qty", "Taxable", "GST"], rows)
    if report == "stock":
        rep = report_service.stock_report(db, tenant_id)
        rows = [[r["product_code"], r["name"], r["unit"], r["current_stock"], r["purchase_price"],
                 r["stock_value"]] for r in rep["rows"]]
        rows.append(["", "TOTAL", "", "", "", rep["total_value"]])
        return ("current-stock", "Current Stock Report",
                ["Code", "Name", "Unit", "Stock", "Cost", "Value"], rows)
    raise AppError(f"Unknown report '{report}'.")


@router.get("/{report}/export")
def export_report(
    report: str,
    db: DbSession,
    tenant_id: TenantId,
    format: Literal["pdf", "excel"] = Query(...),
    day: date = Query(default_factory=date.today, alias="date"),
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    from_date: date = Query(default_factory=lambda: _month_start(date.today())),
    to_date: date = Query(default_factory=date.today),
):
    filename, title, columns, rows = _build_table(
        db, tenant_id, report, day=day, year=year, month=month, from_date=from_date, to_date=to_date
    )
    if format == "excel":
        content = export_service.to_excel(title, columns, rows)
        media, ext = export_service.EXCEL_MIME, "xlsx"
    else:
        content = export_service.to_pdf(title, columns, rows)
        media, ext = export_service.PDF_MIME, "pdf"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{ext}"'},
    )
