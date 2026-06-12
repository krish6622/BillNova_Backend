"""Products router. Read/search for any authenticated user; edit is Owner-only.
Products are created via purchases (no direct create); deletion is not allowed."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, TenantId, require_owner
from app.schemas.common import Page
from app.schemas.product import ProductOut, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=Page[ProductOut])
def list_products(
    db: DbSession,
    tenant_id: TenantId,
    _user: CurrentUser,
    search: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[ProductOut]:
    rows, total = product_service.list_products(
        db, tenant_id, search=search, page=page, limit=limit, active=active
    )
    return Page[ProductOut](
        items=[ProductOut.model_validate(p) for p in rows], total=total, page=page, limit=limit
    )


@router.get("/recent", response_model=list[ProductOut])
def recent(db: DbSession, tenant_id: TenantId, _user: CurrentUser, limit: int = Query(default=12, ge=1, le=50)):
    return [ProductOut.model_validate(p) for p in product_service.recent_products(db, tenant_id, limit=limit)]


@router.get("/top-selling", response_model=list[ProductOut])
def top_selling(db: DbSession, tenant_id: TenantId, _user: CurrentUser, limit: int = Query(default=12, ge=1, le=50)):
    return [ProductOut.model_validate(p) for p in product_service.top_selling_products(db, tenant_id, limit=limit)]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: DbSession, tenant_id: TenantId, _user: CurrentUser) -> ProductOut:
    return ProductOut.model_validate(product_service.get_product(db, tenant_id, product_id))


@router.put("/{product_id}", response_model=ProductOut, dependencies=[Depends(require_owner)])
def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: DbSession, tenant_id: TenantId) -> ProductOut:
    return ProductOut.model_validate(product_service.update_product(db, tenant_id, product_id, payload))
