"""Billing / POS router. Available to any authenticated user (Owner + Cashier)."""

import uuid

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession, TenantId
from app.models.tenant import Tenant
from app.schemas.common import Page
from app.schemas.sale import (
    InvoiceBusiness,
    InvoiceOut,
    SaleCreate,
    SaleListItem,
    SaleOut,
    SalePreviewOut,
    SalePreviewRequest,
)
from app.services import billing_service

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/preview", response_model=SalePreviewOut)
def preview_sale(payload: SalePreviewRequest, db: DbSession, tenant_id: TenantId, _u: CurrentUser) -> SalePreviewOut:
    return SalePreviewOut(**billing_service.preview(db, tenant_id, payload))


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleCreate, db: DbSession, tenant_id: TenantId, user: CurrentUser) -> SaleOut:
    sale = billing_service.create_sale(db, tenant_id, user.id, payload)
    return SaleOut.model_validate(sale)


@router.get("", response_model=Page[SaleListItem])
def list_sales(
    db: DbSession,
    tenant_id: TenantId,
    _u: CurrentUser,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[SaleListItem]:
    rows, total = billing_service.list_sales(db, tenant_id, page=page, limit=limit)
    return Page[SaleListItem](
        items=[SaleListItem.model_validate(s) for s in rows], total=total, page=page, limit=limit
    )


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: uuid.UUID, db: DbSession, tenant_id: TenantId, _u: CurrentUser) -> SaleOut:
    return SaleOut.model_validate(billing_service.get_sale(db, tenant_id, sale_id))


@router.get("/{sale_id}/invoice", response_model=InvoiceOut)
def get_invoice(sale_id: uuid.UUID, db: DbSession, tenant_id: TenantId, _u: CurrentUser) -> InvoiceOut:
    sale = billing_service.get_sale(db, tenant_id, sale_id)
    tenant = db.get(Tenant, tenant_id)
    return InvoiceOut(
        business=InvoiceBusiness.model_validate(tenant),
        sale=SaleOut.model_validate(sale),
    )
