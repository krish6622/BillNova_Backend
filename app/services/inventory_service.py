"""Inventory: current stock, ledger, manual adjustment, low-stock — Owner-only."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.inventory import REF_ADJUSTMENT, TXN_ADJUST, InventoryTransaction
from app.models.product import Product


def _stock_value(p: Product) -> float:
    return float(Decimal(str(p.current_stock)) * Decimal(str(p.purchase_price)))


def stock_list(
    db: Session, tenant_id: uuid.UUID, *, search: str | None, page: int, limit: int
) -> tuple[list[dict], int]:
    conditions = [Product.tenant_id == tenant_id, Product.is_active.is_(True)]
    if search:
        like = f"%{search.lower()}%"
        conditions.append(func.lower(Product.name).like(like))

    total = db.scalar(select(func.count(Product.id)).where(*conditions)) or 0
    rows = db.scalars(
        select(Product).where(*conditions).order_by(Product.name).offset((page - 1) * limit).limit(limit)
    ).all()
    items = [
        {
            "product_id": p.id,
            "product_code": p.product_code,
            "name": p.name,
            "unit": p.unit,
            "current_stock": float(p.current_stock),
            "reorder_level": float(p.reorder_level),
            "purchase_price": float(p.purchase_price),
            "stock_value": _stock_value(p),
        }
        for p in rows
    ]
    return items, total


def ledger(db: Session, tenant_id: uuid.UUID, product_id: uuid.UUID) -> list[InventoryTransaction]:
    product = db.get(Product, product_id)
    if product is None or product.tenant_id != tenant_id:
        raise NotFoundError("Product not found.")
    return list(
        db.scalars(
            select(InventoryTransaction)
            .where(
                InventoryTransaction.tenant_id == tenant_id,
                InventoryTransaction.product_id == product_id,
            )
            .order_by(InventoryTransaction.created_at)
        )
    )


def adjust(db: Session, tenant_id: uuid.UUID, *, product_id: uuid.UUID, delta: float, reason: str) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.tenant_id != tenant_id:
        raise NotFoundError("Product not found.")
    new_balance = Decimal(str(product.current_stock)) + Decimal(str(delta))
    product.current_stock = new_balance
    db.add(
        InventoryTransaction(
            tenant_id=tenant_id,
            product_id=product_id,
            type=TXN_ADJUST,
            quantity=Decimal(str(delta)),
            balance_after=new_balance,
            ref_type=REF_ADJUSTMENT,
            reason=reason,
        )
    )
    db.commit()
    db.refresh(product)
    return product


def low_stock(db: Session, tenant_id: uuid.UUID) -> list[dict]:
    rows = db.scalars(
        select(Product)
        .where(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.reorder_level > 0,
            Product.current_stock <= Product.reorder_level,
        )
        .order_by(Product.name)
    ).all()
    return [
        {
            "product_id": p.id,
            "product_code": p.product_code,
            "name": p.name,
            "unit": p.unit,
            "current_stock": float(p.current_stock),
            "reorder_level": float(p.reorder_level),
            "purchase_price": float(p.purchase_price),
            "stock_value": _stock_value(p),
        }
        for p in rows
    ]
