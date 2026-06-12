"""Suppliers router (Owner-only)."""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import DbSession, TenantId, require_owner
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate
from app.services import supplier_service

router = APIRouter(prefix="/suppliers", tags=["suppliers"], dependencies=[Depends(require_owner)])


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: DbSession, tenant_id: TenantId) -> list[SupplierOut]:
    return [SupplierOut.model_validate(s) for s in supplier_service.list_suppliers(db, tenant_id)]


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, db: DbSession, tenant_id: TenantId) -> SupplierOut:
    return SupplierOut.model_validate(supplier_service.create_supplier(db, tenant_id, payload))


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: uuid.UUID, payload: SupplierUpdate, db: DbSession, tenant_id: TenantId) -> SupplierOut:
    return SupplierOut.model_validate(supplier_service.update_supplier(db, tenant_id, supplier_id, payload))
