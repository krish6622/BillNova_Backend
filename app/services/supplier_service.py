"""Supplier management (Owner-only)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def list_suppliers(db: Session, tenant_id: uuid.UUID) -> list[Supplier]:
    return list(
        db.scalars(
            select(Supplier).where(Supplier.tenant_id == tenant_id).order_by(Supplier.name)
        )
    )


def create_supplier(db: Session, tenant_id: uuid.UUID, payload: SupplierCreate) -> Supplier:
    supplier = Supplier(tenant_id=tenant_id, **payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session, tenant_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierUpdate
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.tenant_id != tenant_id:
        raise NotFoundError("Supplier not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier
