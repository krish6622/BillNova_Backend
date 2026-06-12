"""Products router. Reads allowed for any authenticated user (Owner/Cashier);
writes are Owner-only."""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, TenantId, require_owner
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
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


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: DbSession, tenant_id: TenantId, _user: CurrentUser) -> ProductOut:
    return ProductOut.model_validate(product_service.get_product(db, tenant_id, product_id))


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_owner)])
def create_product(payload: ProductCreate, db: DbSession, tenant_id: TenantId) -> ProductOut:
    return ProductOut.model_validate(product_service.create_product(db, tenant_id, payload))


@router.put("/{product_id}", response_model=ProductOut, dependencies=[Depends(require_owner)])
def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: DbSession, tenant_id: TenantId) -> ProductOut:
    return ProductOut.model_validate(product_service.update_product(db, tenant_id, product_id, payload))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_owner)])
def delete_product(product_id: uuid.UUID, db: DbSession, tenant_id: TenantId) -> None:
    product_service.delete_product(db, tenant_id, product_id)
