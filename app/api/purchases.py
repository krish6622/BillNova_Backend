"""Purchases router (Owner-only)."""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import DbSession, TenantId, require_owner
from app.schemas.common import Page
from app.schemas.purchase import PurchaseCreate, PurchaseListItem, PurchaseOut
from app.services import purchase_service

router = APIRouter(prefix="/purchases", tags=["purchases"], dependencies=[Depends(require_owner)])


@router.get("", response_model=Page[PurchaseListItem])
def list_purchases(
    db: DbSession,
    tenant_id: TenantId,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[PurchaseListItem]:
    rows, total = purchase_service.list_purchases(db, tenant_id, page=page, limit=limit)
    return Page[PurchaseListItem](
        items=[PurchaseListItem.model_validate(p) for p in rows], total=total, page=page, limit=limit
    )


@router.get("/{purchase_id}", response_model=PurchaseOut)
def get_purchase(purchase_id: uuid.UUID, db: DbSession, tenant_id: TenantId) -> PurchaseOut:
    return PurchaseOut.model_validate(purchase_service.get_purchase(db, tenant_id, purchase_id))


@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
def create_purchase(payload: PurchaseCreate, db: DbSession, tenant_id: TenantId) -> PurchaseOut:
    return PurchaseOut.model_validate(purchase_service.create_purchase(db, tenant_id, payload))


@router.post("/{purchase_id}/cancel", response_model=PurchaseOut)
def cancel_purchase(purchase_id: uuid.UUID, db: DbSession, tenant_id: TenantId) -> PurchaseOut:
    return PurchaseOut.model_validate(purchase_service.cancel_purchase(db, tenant_id, purchase_id))
