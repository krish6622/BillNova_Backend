"""CR-5 — Invoice Register: list/filter, void (with stock reversal), and A4 PDF.

The register is a managed view over `sales`. Reprint is just re-fetching the invoice
payload (no state change); void is the only mutation and it reverses stock + usage.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.inventory import REF_SALE, TXN_IN, InventoryTransaction
from app.models.payment import Payment
from app.models.product import Product
from app.models.sale import BILLING_WITH_GST, STATUS_VOID, Sale
from app.models.tenant import Tenant
from app.models.user import User
from app.services import billing_service, subscription_service
from app.services.pricing import customer_unit_rate, net_unit_rate


def list_invoices(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    page: int,
    limit: int,
    date_from: date | None = None,
    date_to: date | None = None,
    invoice_number: str | None = None,
    payment_mode: str | None = None,
    cashier_id: uuid.UUID | None = None,
    status: str | None = None,
    billing_type: str | None = None,
    is_gst_customer: bool | None = None,
) -> tuple[list[dict], int]:
    conds = [Sale.tenant_id == tenant_id]
    if status:
        conds.append(Sale.status == status)
    if billing_type:
        conds.append(Sale.billing_type == billing_type)
    if is_gst_customer is not None:
        conds.append(Sale.is_gst_customer.is_(is_gst_customer))
    if date_from:
        conds.append(func.date(Sale.created_at) >= date_from)
    if date_to:
        conds.append(func.date(Sale.created_at) <= date_to)
    if invoice_number:
        conds.append(Sale.invoice_number.ilike(f"%{invoice_number}%"))
    if cashier_id:
        conds.append(Sale.created_by == cashier_id)
    if payment_mode:
        conds.append(
            Sale.id.in_(
                select(Payment.sale_id).where(
                    Payment.tenant_id == tenant_id, Payment.mode == payment_mode
                )
            )
        )

    total = db.scalar(select(func.count(Sale.id)).where(*conds)) or 0
    rows = list(
        db.scalars(
            select(Sale)
            .where(*conds)
            .order_by(Sale.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )

    # Resolve cashier names in one query (avoid N+1).
    cashier_ids = {s.created_by for s in rows if s.created_by}
    names: dict[uuid.UUID, str] = {}
    if cashier_ids:
        names = {
            u.id: u.name
            for u in db.scalars(select(User).where(User.id.in_(cashier_ids)))
        }

    items = [
        {
            "id": s.id,
            "invoice_number": s.invoice_number,
            "created_at": s.created_at,
            "customer_name": s.customer_name,
            "is_gst_customer": s.is_gst_customer,
            "customer_gstin": s.customer_gstin,
            "billing_type": s.billing_type,
            "grand_total": float(s.grand_total),
            "payment_modes": sorted({p.mode for p in s.payments}),
            "cashier_name": names.get(s.created_by) if s.created_by else None,
            "show_gst_on_invoice": s.show_gst_on_invoice,
            "status": s.status,
        }
        for s in rows
    ]
    return items, total


def list_cashiers(db: Session, tenant_id: uuid.UUID) -> list[User]:
    """Users of the tenant — to populate the register's Cashier filter."""
    return list(
        db.scalars(select(User).where(User.tenant_id == tenant_id).order_by(User.name))
    )


def cashier_name(db: Session, sale: Sale) -> str | None:
    """Resolve the name of the user who created the sale (for the invoice header)."""
    if not sale.created_by:
        return None
    user = db.get(User, sale.created_by)
    return user.name if user else None


def void_invoice(db: Session, tenant_id: uuid.UUID, sale_id: uuid.UUID) -> Sale:
    """Void an invoice: mark it, return its stock to inventory, and reverse the bill
    from this month's usage. Idempotent guard against double-void."""
    sale = billing_service.get_sale(db, tenant_id, sale_id)
    if sale.status == STATUS_VOID:
        raise AppError("Invoice is already voided.")

    for item in sale.items:
        product = db.get(Product, item.product_id)
        if product is None:
            continue
        qty = Decimal(str(item.quantity))
        new_balance = Decimal(str(product.current_stock)) + qty
        product.current_stock = new_balance
        db.add(
            InventoryTransaction(
                tenant_id=tenant_id,
                product_id=product.id,
                type=TXN_IN,
                quantity=qty,
                balance_after=new_balance,
                ref_type=REF_SALE,
                ref_id=sale.id,
                reason="Invoice voided",
            )
        )

    sale.status = STATUS_VOID
    sale.voided_at = datetime.now(timezone.utc)
    # Reverse usage for the month the sale belongs to (not necessarily the current one).
    subscription_service.decrement_usage(db, tenant_id, today=sale.created_at.date())
    db.commit()
    return billing_service.get_sale(db, tenant_id, sale_id)


def invoice_pdf(db: Session, tenant_id: uuid.UUID, sale_id: uuid.UUID) -> bytes:
    """Render the A4 invoice as a PDF (reportlab). Honours show_gst_on_invoice like the
    on-screen/thermal invoice — hidden mode prints Item/Qty/Rate/Amount only."""
    sale = billing_service.get_sale(db, tenant_id, sale_id)
    tenant = db.get(Tenant, tenant_id)
    # CR-7: per-bill, not the tenant setting. A WITHOUT_GST sale has no GST to show.
    show_gst = sale.show_gst_on_invoice and sale.billing_type == BILLING_WITH_GST

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.4 * cm, bottomMargin=1.2 * cm)

    title = "TAX INVOICE" if show_gst else "INVOICE"
    header_bits = [f"<b>{tenant.business_name}</b>"]
    if tenant.address:
        header_bits.append(tenant.address)
    header_bits.append(f"Ph: {tenant.mobile}")
    if tenant.gst_number:  # GSTIN shown whenever configured
        header_bits.append(f"GSTIN: {tenant.gst_number}")
    flow = [
        Paragraph("<br/>".join(header_bits), styles["Normal"]),
        Spacer(1, 8),
        Paragraph(
            f"<b>{title}</b> &nbsp; {sale.invoice_number}<br/>"
            f"Date: {sale.created_at.strftime('%d-%m-%Y %I:%M %p')}<br/>"
            f"Cashier: {cashier_name(db, sale) or '—'}<br/>"
            f"Customer: {sale.customer_name or 'Walk-in'}"
            + (f"<br/>Customer GSTIN: {sale.customer_gstin}" if sale.customer_gstin else "")
            + ("<br/><font color='red'><b>VOID</b></font>" if sale.status == STATUS_VOID else ""),
            styles["Normal"],
        ),
        Spacer(1, 10),
    ]

    # CR-6: a printed line must satisfy quantity × rate == amount.
    #   hidden  -> rate = customer (GST-inclusive) per-unit ; amount = line_total
    #   visible -> rate = net (pre-GST) per-unit            ; amount = taxable ; GST shown below
    cols = ["Item", "Qty", "Rate", "Amount"]
    data = [cols] + [
        [
            it.product_name,
            f"{float(it.quantity):g} {it.unit}",
            f"{float(customer_unit_rate(it.line_total, it.quantity)):.2f}"
            if not show_gst
            else f"{float(net_unit_rate(it.taxable_value, it.quantity)):.2f}",
            f"{float(it.line_total):.2f}" if not show_gst else f"{float(it.taxable_value):.2f}",
        ]
        for it in sale.items
    ]

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    flow += [table, Spacer(1, 12)]

    totals = []
    if show_gst:
        totals.append(["Taxable", f"{float(sale.total_taxable):.2f}"])
        if float(sale.total_cgst):
            totals.append(["CGST", f"{float(sale.total_cgst):.2f}"])
        if float(sale.total_sgst):
            totals.append(["SGST", f"{float(sale.total_sgst):.2f}"])
        if float(sale.total_igst):
            totals.append(["IGST", f"{float(sale.total_igst):.2f}"])
    if float(sale.total_discount):
        totals.append(["Discount", f"- {float(sale.total_discount):.2f}"])
    total_row = len(totals)  # the bold/ruled grand-total row
    totals.append(["TOTAL", f"{float(sale.grand_total):.2f}"])
    paid = sum(float(p.amount) for p in sale.payments)
    for p in sale.payments:
        totals.append([p.mode.upper(), f"{float(p.amount):.2f}"])
    totals.append(["BALANCE", f"{paid - float(sale.grand_total):.2f}"])

    tt = Table(totals, colWidths=[5 * cm, 5 * cm], hAlign="RIGHT")
    tt.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, total_row), (-1, total_row), 0.5, colors.black),
                ("FONTNAME", (0, total_row), (-1, total_row), "Helvetica-Bold"),
            ]
        )
    )
    flow.append(tt)
    flow += [Spacer(1, 14), Paragraph("Thank You For Shopping! Please Visit Again", styles["Italic"])]
    if tenant.invoice_footer:
        flow.append(Paragraph(tenant.invoice_footer, styles["Italic"]))
    if tenant.show_branding:
        flow.append(Paragraph("<font size=8 color='#888'>Powered by BillNova</font>", styles["Normal"]))

    doc.build(flow)
    return buf.getvalue()
