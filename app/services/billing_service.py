"""Billing / POS logic: cart preview and atomic invoice save."""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import InsufficientStockError, NotFoundError, PaymentMismatchError
from app.models.inventory import REF_SALE, TXN_OUT, InventoryTransaction
from app.models.payment import Payment
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.tenant import Tenant
from app.schemas.sale import SaleCreate, SalePreviewRequest
from app.services import gst_service, subscription_service
from app.services.gst_service import LineInput, compute_bill

TWO = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO, rounding=ROUND_HALF_UP)


def _resolve_modes(db: Session, tenant_id: uuid.UUID, payload: SalePreviewRequest) -> tuple[str, str, Tenant]:
    tenant = db.get(Tenant, tenant_id)
    gst_mode = payload.gst_mode or tenant.gst_mode_default
    place = payload.place_of_supply or tenant.place_of_supply
    return gst_mode, place, tenant


def _load_products(db: Session, tenant_id: uuid.UUID, items) -> dict[uuid.UUID, Product]:
    ids = [item.product_id for item in items]
    rows = db.scalars(
        select(Product).where(Product.tenant_id == tenant_id, Product.id.in_(ids))
    ).all()
    by_id = {p.id: p for p in rows}
    for pid in ids:
        if pid not in by_id:
            raise NotFoundError("Product not found.", {"product_id": str(pid)})
    return by_id


def _line_inputs(items, products) -> list[LineInput]:
    return [
        LineInput(
            unit_price=products[item.product_id].selling_price,
            quantity=item.quantity,
            gst_percentage=products[item.product_id].gst_percentage,
            discount=item.discount,
        )
        for item in items
    ]


def preview(db: Session, tenant_id: uuid.UUID, payload: SalePreviewRequest) -> dict:
    gst_mode, place, _ = _resolve_modes(db, tenant_id, payload)
    products = _load_products(db, tenant_id, payload.items)
    comp = compute_bill(
        _line_inputs(payload.items, products),
        gst_mode=gst_mode,
        place_of_supply=place,
        bill_discount=payload.bill_discount,
    )
    items_out = []
    for item, cline in zip(payload.items, comp.lines, strict=True):
        p = products[item.product_id]
        items_out.append(
            {
                "product_id": p.id,
                "product_name": p.name,
                "hsn_code": p.hsn_code,
                "quantity": item.quantity,
                "unit_price": float(p.selling_price),
                "gst_percentage": float(p.gst_percentage),
                "discount": float(cline.discount),
                "taxable_value": float(cline.taxable_value),
                "cgst": float(cline.cgst),
                "sgst": float(cline.sgst),
                "igst": float(cline.igst),
                "line_total": float(cline.line_total),
            }
        )
    return {
        "gst_mode": gst_mode,
        "place_of_supply": place,
        "items": items_out,
        "totals": _totals_dict(comp),
    }


def _totals_dict(comp: gst_service.BillComputation) -> dict:
    return {
        "total_taxable": float(comp.total_taxable),
        "total_discount": float(comp.total_discount),
        "total_cgst": float(comp.total_cgst),
        "total_sgst": float(comp.total_sgst),
        "total_igst": float(comp.total_igst),
        "total_gst": float(comp.total_gst),
        "grand_total": float(comp.grand_total),
    }


def _next_invoice_number(db: Session, tenant_id: uuid.UUID, *, today: date) -> str:
    prefix = f"INV-{today.year}-"
    count = db.scalar(
        select(func.count(Sale.id)).where(
            Sale.tenant_id == tenant_id, Sale.invoice_number.like(f"{prefix}%")
        )
    ) or 0
    return f"{prefix}{count + 1:04d}"


def create_sale(
    db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID, payload: SaleCreate, *, today: date | None = None
) -> Sale:
    today = today or date.today()

    # 1) Subscription guard (inactive / over-limit) — raises before any writes.
    subscription_service.assert_can_bill(db, tenant_id)

    gst_mode, place, _ = _resolve_modes(db, tenant_id, payload)
    products = _load_products(db, tenant_id, payload.items)

    # 2) Stock check (default policy: block on insufficient stock).
    for item in payload.items:
        p = products[item.product_id]
        if Decimal(str(p.current_stock)) < Decimal(str(item.quantity)):
            raise InsufficientStockError(
                f"Insufficient stock for '{p.name}'.",
                {"product_id": str(p.id), "available": float(p.current_stock), "requested": item.quantity},
            )

    comp = compute_bill(
        _line_inputs(payload.items, products),
        gst_mode=gst_mode,
        place_of_supply=place,
        bill_discount=payload.bill_discount,
    )

    # 3) Payments must sum to the grand total.
    pay_sum = sum((Decimal(str(p.amount)) for p in payload.payments), Decimal("0"))
    if _q(pay_sum) != _q(comp.grand_total):
        raise PaymentMismatchError(
            "Payments do not sum to the grand total.",
            {"grand_total": float(comp.grand_total), "paid": float(pay_sum)},
        )

    # 4) Atomic write: sale + items + payments + stock movements + usage.
    sale = Sale(
        tenant_id=tenant_id,
        invoice_number=_next_invoice_number(db, tenant_id, today=today),
        created_by=user_id,
        gst_mode=gst_mode,
        place_of_supply=place,
        total_taxable=comp.total_taxable,
        total_discount=comp.total_discount,
        total_cgst=comp.total_cgst,
        total_sgst=comp.total_sgst,
        total_igst=comp.total_igst,
        total_gst=comp.total_gst,
        grand_total=comp.grand_total,
        notes=payload.notes,
    )
    db.add(sale)
    db.flush()  # assign sale.id

    for item, cline in zip(payload.items, comp.lines, strict=True):
        p = products[item.product_id]
        db.add(
            SaleItem(
                tenant_id=tenant_id,
                sale_id=sale.id,
                product_id=p.id,
                product_name=p.name,
                hsn_code=p.hsn_code,
                quantity=item.quantity,
                unit_price=p.selling_price,
                discount=cline.discount,
                gst_percentage=p.gst_percentage,
                taxable_value=cline.taxable_value,
                cgst=cline.cgst,
                sgst=cline.sgst,
                igst=cline.igst,
                line_total=cline.line_total,
                notes=item.notes,
            )
        )
        new_balance = Decimal(str(p.current_stock)) - Decimal(str(item.quantity))
        p.current_stock = new_balance
        db.add(
            InventoryTransaction(
                tenant_id=tenant_id,
                product_id=p.id,
                type=TXN_OUT,
                quantity=-Decimal(str(item.quantity)),
                balance_after=new_balance,
                ref_type=REF_SALE,
                ref_id=sale.id,
            )
        )

    for pay in payload.payments:
        db.add(
            Payment(
                tenant_id=tenant_id, sale_id=sale.id, mode=pay.mode,
                amount=pay.amount, reference=pay.reference,
            )
        )

    subscription_service.increment_usage(db, tenant_id, today=today)
    db.commit()
    return get_sale(db, tenant_id, sale.id)


def get_sale(db: Session, tenant_id: uuid.UUID, sale_id: uuid.UUID) -> Sale:
    sale = db.get(Sale, sale_id)
    if sale is None or sale.tenant_id != tenant_id:
        raise NotFoundError("Sale not found.")
    return sale


def list_sales(db: Session, tenant_id: uuid.UUID, *, page: int, limit: int) -> tuple[list[Sale], int]:
    total = db.scalar(select(func.count(Sale.id)).where(Sale.tenant_id == tenant_id)) or 0
    rows = list(
        db.scalars(
            select(Sale)
            .where(Sale.tenant_id == tenant_id)
            .order_by(Sale.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    return rows, total
