"""Product management logic (Owner-only writes)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DuplicateError, NotFoundError
from app.models.product import Product
from app.models.purchase import PurchaseItem
from app.models.sale import SaleItem
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


def _repo(db: Session, tenant_id: uuid.UUID) -> ProductRepository:
    return ProductRepository(db, tenant_id)


def list_products(db, tenant_id, *, search, page, limit, active):
    rows, total = _repo(db, tenant_id).search(search=search, page=page, limit=limit, active=active)
    return rows, total


def get_product(db, tenant_id, product_id: uuid.UUID) -> Product:
    product = _repo(db, tenant_id).get(product_id)
    if product is None:
        raise NotFoundError("Product not found.")
    return product


def create_product(db, tenant_id, payload: ProductCreate) -> Product:
    repo = _repo(db, tenant_id)
    if repo.code_exists(payload.product_code):
        raise DuplicateError("A product with this code already exists.")
    product = Product(tenant_id=tenant_id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db, tenant_id, product_id: uuid.UUID, payload: ProductUpdate) -> Product:
    product = get_product(db, tenant_id, product_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def _is_referenced(db: Session, product_id: uuid.UUID) -> bool:
    in_sales = db.scalar(select(SaleItem.id).where(SaleItem.product_id == product_id).limit(1))
    in_purchases = db.scalar(
        select(PurchaseItem.id).where(PurchaseItem.product_id == product_id).limit(1)
    )
    return in_sales is not None or in_purchases is not None


def delete_product(db, tenant_id, product_id: uuid.UUID) -> bool:
    """Soft-delete (deactivate) a product referenced by sales/purchases to preserve
    history; hard-delete a never-referenced product. Returns True if soft-deleted."""
    product = get_product(db, tenant_id, product_id)
    if _is_referenced(db, product_id):
        product.is_active = False
        db.commit()
        return True
    db.delete(product)
    db.commit()
    return False
