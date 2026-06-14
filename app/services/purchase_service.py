"""Purchase logic — saving increases stock; cancelling reverses it. Owner-only."""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.inventory import REF_PURCHASE, TXN_IN, TXN_OUT, InventoryTransaction
from app.models.product import Product
from app.models.purchase import STATUS_CANCELLED, Purchase, PurchaseItem
from app.schemas.purchase import PurchaseCreate
from app.services import product_service

TWO = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO, rounding=ROUND_HALF_UP)


def _resolve_product(db: Session, tenant_id: uuid.UUID, item) -> Product:
    """Return the product for a purchase line — fetch existing, or create inline.
    Inline creation auto-generates/validates the code (duplicate rejects the purchase)."""
    if item.product_id is not None:
        product = db.get(Product, item.product_id)
        if product is None or product.tenant_id != tenant_id:
            raise NotFoundError("Product not found.", {"product_id": str(item.product_id)})
        product_service.apply_purchase_pricing(
            product,
            purchase_price=item.purchase_price,
            markup_amount=item.markup_amount,
            gst_percentage=item.gst_percentage,
            hsn_code=item.hsn_code,
            unit=item.unit,
        )
        return product
    return product_service.create_from_purchase(
        db,
        tenant_id,
        product_code=item.product_code,
        name=item.product_name,
        hsn_code=item.hsn_code,
        gst_percentage=item.gst_percentage,
        unit=item.unit,
        purchase_price=item.purchase_price,
        markup_amount=item.markup_amount,
    )


def create_purchase(db: Session, tenant_id: uuid.UUID, payload: PurchaseCreate) -> Purchase:
    purchase = Purchase(
        tenant_id=tenant_id,
        supplier_id=payload.supplier_id,
        supplier_name=payload.supplier_name,
        invoice_number=payload.invoice_number,
        notes=payload.notes,
        purchase_date=payload.purchase_date,
    )
    db.add(purchase)
    db.flush()

    total_amount = Decimal("0")
    total_gst = Decimal("0")
    for item in payload.items:
        p = _resolve_product(db, tenant_id, item)
        qty = Decimal(str(item.quantity))
        price = Decimal(str(item.purchase_price))
        rate = Decimal(str(item.gst_percentage))
        base = qty * price
        gst_amount = _q(base * rate / 100)
        line_total = _q(base + gst_amount)
        total_amount += line_total
        total_gst += gst_amount

        db.add(
            PurchaseItem(
                tenant_id=tenant_id,
                purchase_id=purchase.id,
                product_id=p.id,
                product_name=p.name,
                quantity=qty,
                purchase_price=price,
                gst_percentage=rate,
                gst_amount=gst_amount,
                line_total=line_total,
            )
        )

        new_balance = Decimal(str(p.current_stock)) + qty
        p.current_stock = new_balance
        p.purchase_price = price  # keep latest cost
        db.add(
            InventoryTransaction(
                tenant_id=tenant_id,
                product_id=p.id,
                type=TXN_IN,
                quantity=qty,
                balance_after=new_balance,
                ref_type=REF_PURCHASE,
                ref_id=purchase.id,
            )
        )

    purchase.total_amount = _q(total_amount)
    purchase.total_gst = _q(total_gst)
    db.commit()
    return get_purchase(db, tenant_id, purchase.id)


def cancel_purchase(db: Session, tenant_id: uuid.UUID, purchase_id: uuid.UUID) -> Purchase:
    purchase = get_purchase(db, tenant_id, purchase_id)
    if purchase.status == STATUS_CANCELLED:
        raise AppError("Purchase is already cancelled.")

    for item in purchase.items:
        product = db.get(Product, item.product_id)
        if product is None:
            continue
        qty = Decimal(str(item.quantity))
        new_balance = Decimal(str(product.current_stock)) - qty
        product.current_stock = new_balance
        db.add(
            InventoryTransaction(
                tenant_id=tenant_id,
                product_id=product.id,
                type=TXN_OUT,
                quantity=-qty,
                balance_after=new_balance,
                ref_type=REF_PURCHASE,
                ref_id=purchase.id,
                reason="Purchase cancelled",
            )
        )

    purchase.status = STATUS_CANCELLED
    db.commit()
    return get_purchase(db, tenant_id, purchase_id)


def get_purchase(db: Session, tenant_id: uuid.UUID, purchase_id: uuid.UUID) -> Purchase:
    purchase = db.get(Purchase, purchase_id)
    if purchase is None or purchase.tenant_id != tenant_id:
        raise NotFoundError("Purchase not found.")
    return purchase


def list_purchases(
    db: Session, tenant_id: uuid.UUID, *, page: int, limit: int
) -> tuple[list[Purchase], int]:
    total = db.scalar(select(func.count(Purchase.id)).where(Purchase.tenant_id == tenant_id)) or 0
    rows = list(
        db.scalars(
            select(Purchase)
            .where(Purchase.tenant_id == tenant_id)
            .order_by(Purchase.purchase_date.desc(), Purchase.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    return rows, total
