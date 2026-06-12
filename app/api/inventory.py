"""Inventory router (Owner-only)."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, TenantId, require_owner
from app.schemas.common import Page
from app.schemas.inventory import AdjustmentRequest, LedgerEntry, StockItem
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(require_owner)])


@router.get("/stock", response_model=Page[StockItem])
def stock(
    db: DbSession,
    tenant_id: TenantId,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[StockItem]:
    items, total = inventory_service.stock_list(db, tenant_id, search=search, page=page, limit=limit)
    return Page[StockItem](items=[StockItem(**i) for i in items], total=total, page=page, limit=limit)


@router.get("/ledger/{product_id}", response_model=list[LedgerEntry])
def ledger(product_id: uuid.UUID, db: DbSession, tenant_id: TenantId) -> list[LedgerEntry]:
    return [LedgerEntry.model_validate(e) for e in inventory_service.ledger(db, tenant_id, product_id)]


@router.post("/adjust", response_model=StockItem)
def adjust(payload: AdjustmentRequest, db: DbSession, tenant_id: TenantId) -> StockItem:
    p = inventory_service.adjust(
        db, tenant_id, product_id=payload.product_id, delta=payload.delta, reason=payload.reason
    )
    return StockItem(
        product_id=p.id, product_code=p.product_code, name=p.name, unit=p.unit,
        current_stock=float(p.current_stock), reorder_level=float(p.reorder_level),
        purchase_price=float(p.purchase_price),
        stock_value=float(p.current_stock) * float(p.purchase_price),
    )


@router.get("/low-stock", response_model=list[StockItem])
def low_stock(db: DbSession, tenant_id: TenantId) -> list[StockItem]:
    return [StockItem(**i) for i in inventory_service.low_stock(db, tenant_id)]
