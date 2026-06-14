"""Product catalogue logic.

Products are NOT created directly — they are created via purchases (see
purchase_service). This module exposes read/search/edit, auto product-code
generation, and the internal create/update-from-purchase helpers. Selling price
is always derived as purchase_price + markup_amount (CR-3).
"""

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DuplicateError, NotFoundError
from app.models.product import Product
from app.models.sale import STATUS_VOID, Sale, SaleItem
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductUpdate
from app.services.pricing import compute_selling_price

_CODE_RE = re.compile(r"^PD-(\d+)$")


def _repo(db: Session, tenant_id: uuid.UUID) -> ProductRepository:
    return ProductRepository(db, tenant_id)


# ---- reads --------------------------------------------------------------

def list_products(db, tenant_id, *, search, page, limit, active):
    return _repo(db, tenant_id).search(search=search, page=page, limit=limit, active=active)


def get_product(db, tenant_id, product_id: uuid.UUID) -> Product:
    product = _repo(db, tenant_id).get(product_id)
    if product is None:
        raise NotFoundError("Product not found.")
    return product


def recent_products(db: Session, tenant_id: uuid.UUID, *, limit: int = 12) -> list[Product]:
    return list(
        db.scalars(
            select(Product)
            .where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
    )


def top_selling_products(db: Session, tenant_id: uuid.UUID, *, limit: int = 12) -> list[Product]:
    """Active products ranked by total quantity sold (all time), for POS quick-add."""
    ranked = (
        select(SaleItem.product_id, func.sum(SaleItem.quantity).label("qty"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(SaleItem.tenant_id == tenant_id, Sale.status != STATUS_VOID)  # CR-5: skip voided
        .group_by(SaleItem.product_id)
        .subquery()
    )
    rows = db.scalars(
        select(Product)
        .join(ranked, ranked.c.product_id == Product.id)
        .where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
        .order_by(ranked.c.qty.desc())
        .limit(limit)
    ).all()
    return list(rows)


# ---- edit ---------------------------------------------------------------

def update_product(db, tenant_id, product_id: uuid.UUID, payload: ProductUpdate) -> Product:
    product = get_product(db, tenant_id, product_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(product, field, value)
    # Recompute the derived selling price whenever the markup amount changes.
    if "markup_amount" in data:
        product.selling_price = compute_selling_price(
            product.purchase_price, product.markup_amount
        )
    db.commit()
    db.refresh(product)
    return product


# ---- internal helpers used by purchases ---------------------------------

def next_product_code(db: Session, tenant_id: uuid.UUID) -> str:
    """Next auto code PD-#####, tenant-scoped (max existing PD-n + 1)."""
    codes = db.scalars(
        select(Product.product_code).where(
            Product.tenant_id == tenant_id, Product.product_code.like("PD-%")
        )
    ).all()
    highest = 0
    for c in codes:
        m = _CODE_RE.match(c)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"PD-{highest + 1:05d}"


def code_in_use(db: Session, tenant_id: uuid.UUID, code: str) -> bool:
    return _repo(db, tenant_id).code_exists(code)


def create_from_purchase(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    product_code: str | None,
    name: str,
    hsn_code: str | None,
    gst_percentage,
    unit: str,
    purchase_price,
    markup_amount,
) -> Product:
    """Create a product as part of a purchase. Auto-generates the code if not
    given; rejects a duplicate code (within the tenant)."""
    code = (product_code or "").strip() or next_product_code(db, tenant_id)
    if code_in_use(db, tenant_id, code):
        raise DuplicateError(f"Product code '{code}' already exists.")
    product = Product(
        tenant_id=tenant_id,
        product_code=code,
        name=name,
        unit=unit or "NOS",
        hsn_code=hsn_code,
        gst_percentage=gst_percentage,
        purchase_price=purchase_price,
        markup_amount=markup_amount,
        selling_price=compute_selling_price(purchase_price, markup_amount),
        current_stock=0,
    )
    db.add(product)
    db.flush()
    return product


def apply_purchase_pricing(
    product: Product, *, purchase_price, markup_amount, gst_percentage, hsn_code, unit
) -> None:
    """When an existing product is restocked via a purchase, refresh its cost,
    markup amount, derived selling price, and tax fields to the latest purchase."""
    product.purchase_price = purchase_price
    product.markup_amount = markup_amount
    product.gst_percentage = gst_percentage
    if hsn_code is not None:
        product.hsn_code = hsn_code
    if unit:
        product.unit = unit
    product.selling_price = compute_selling_price(purchase_price, markup_amount)
