"""Product management logic (Owner-only writes)."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import DuplicateError, NotFoundError
from app.models.product import Product
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


def delete_product(db, tenant_id, product_id: uuid.UUID) -> None:
    """Hard delete in M2 (nothing references products yet). M4 switches to a
    reference-aware soft delete once sales/purchases can reference a product."""
    product = get_product(db, tenant_id, product_id)
    db.delete(product)
    db.commit()
