"""CR-5 — Invoice Register router.

List / view / reprint are available to any authenticated user (Owner + Cashier).
Void and PDF export are Owner-only (RBAC: invoice:void / invoice:export) — a cashier
may review and reprint bills but cannot reverse or export them.
Tenant isolation is enforced everywhere via get_sale (cross-tenant -> 404)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import CurrentUser, DbSession, TenantId, require_permission
from app.core.permissions import INVOICE_EXPORT, INVOICE_VOID
from app.models.tenant import Tenant
from app.schemas.common import Page
from app.schemas.sale import InvoiceBusiness, InvoiceListItem, InvoiceOut, SaleOut
from app.services import billing_service, invoice_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=Page[InvoiceListItem])
def list_invoices(
    db: DbSession,
    tenant_id: TenantId,
    _u: CurrentUser,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    date_from: date | None = None,
    date_to: date | None = None,
    invoice_number: str | None = None,
    payment_mode: str | None = None,
    cashier_id: uuid.UUID | None = None,
    status: str | None = Query(default=None, pattern="^(active|void)$"),
    billing_type: str | None = Query(default=None, pattern="^(WITH_GST|WITHOUT_GST)$"),
    is_gst_customer: bool | None = None,
) -> Page[InvoiceListItem]:
    items, total = invoice_service.list_invoices(
        db, tenant_id, page=page, limit=limit, date_from=date_from, date_to=date_to,
        invoice_number=invoice_number, payment_mode=payment_mode, cashier_id=cashier_id,
        status=status, billing_type=billing_type, is_gst_customer=is_gst_customer,
    )
    return Page[InvoiceListItem](
        items=[InvoiceListItem.model_validate(i) for i in items], total=total, page=page, limit=limit
    )


@router.get("/cashiers")
def list_cashiers(db: DbSession, tenant_id: TenantId, _u: CurrentUser) -> list[dict]:
    return [{"id": str(u.id), "name": u.name} for u in invoice_service.list_cashiers(db, tenant_id)]


def _invoice_payload(db, tenant_id: uuid.UUID, sale_id: uuid.UUID) -> InvoiceOut:
    sale = billing_service.get_sale(db, tenant_id, sale_id)
    tenant = db.get(Tenant, tenant_id)
    sale_out = SaleOut.model_validate(sale)
    sale_out.cashier_name = invoice_service.cashier_name(db, sale)
    return InvoiceOut(business=InvoiceBusiness.model_validate(tenant), sale=sale_out)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: uuid.UUID, db: DbSession, tenant_id: TenantId, _u: CurrentUser) -> InvoiceOut:
    return _invoice_payload(db, tenant_id, invoice_id)


@router.post("/{invoice_id}/reprint", response_model=InvoiceOut)
def reprint_invoice(invoice_id: uuid.UUID, db: DbSession, tenant_id: TenantId, _u: CurrentUser) -> InvoiceOut:
    # Reprint is a non-mutating re-fetch of the invoice payload; the client prints it.
    return _invoice_payload(db, tenant_id, invoice_id)


@router.post(
    "/{invoice_id}/void",
    response_model=SaleOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(INVOICE_VOID))],
)
def void_invoice(invoice_id: uuid.UUID, db: DbSession, tenant_id: TenantId) -> SaleOut:
    # Owner-only: cashiers may view/reprint but never void (reverses stock + usage).
    sale = invoice_service.void_invoice(db, tenant_id, invoice_id)
    return SaleOut.model_validate(sale)


@router.get("/{invoice_id}/pdf", dependencies=[Depends(require_permission(INVOICE_EXPORT))])
def invoice_pdf(invoice_id: uuid.UUID, db: DbSession, tenant_id: TenantId) -> Response:
    sale = billing_service.get_sale(db, tenant_id, invoice_id)  # 404s cross-tenant before render
    pdf = invoice_service.invoice_pdf(db, tenant_id, invoice_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{sale.invoice_number}.pdf"'},
    )
