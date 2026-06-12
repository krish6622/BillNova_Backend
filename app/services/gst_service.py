"""Pure GST computation engine — no DB, fully unit-testable.

Supports GST-inclusive and GST-exclusive pricing, intra-state (CGST+SGST) and
inter-state (IGST) splits, line-level and bill-level discounts. All money math
uses Decimal with ROUND_HALF_UP to 2 decimals (docs §5.6).
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

TWO = Decimal("0.01")
ZERO = Decimal("0.00")

MODE_INCLUSIVE = "inclusive"
MODE_EXCLUSIVE = "exclusive"
SUPPLY_INTRA = "intra"
SUPPLY_INTER = "inter"


def _d(value) -> Decimal:
    return Decimal(str(value))


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO, rounding=ROUND_HALF_UP)


@dataclass
class LineInput:
    unit_price: Decimal
    quantity: Decimal
    gst_percentage: Decimal
    discount: Decimal = ZERO


@dataclass
class ComputedLine:
    taxable_value: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    gst_amount: Decimal
    discount: Decimal
    line_total: Decimal


@dataclass
class BillComputation:
    lines: list[ComputedLine] = field(default_factory=list)
    total_taxable: Decimal = ZERO
    total_discount: Decimal = ZERO
    total_cgst: Decimal = ZERO
    total_sgst: Decimal = ZERO
    total_igst: Decimal = ZERO
    total_gst: Decimal = ZERO
    grand_total: Decimal = ZERO


def compute_bill(
    lines: list[LineInput],
    *,
    gst_mode: str = MODE_INCLUSIVE,
    place_of_supply: str = SUPPLY_INTRA,
    bill_discount=0,
) -> BillComputation:
    bill_discount = _d(bill_discount)
    grosses = [_d(line.unit_price) * _d(line.quantity) for line in lines]
    total_gross = sum(grosses, ZERO)

    result = BillComputation()
    for line, gross in zip(lines, grosses, strict=True):
        line_disc = _d(line.discount)
        share = bill_discount * (gross / total_gross) if total_gross > 0 and bill_discount > 0 else ZERO
        eff_disc = line_disc + share
        base = gross - eff_disc
        if base < 0:
            base = ZERO

        rate = _d(line.gst_percentage)
        if gst_mode == MODE_INCLUSIVE:
            taxable = base / (1 + rate / 100)
            gst_amount = base - taxable
            line_total = base
        else:
            taxable = base
            gst_amount = base * rate / 100
            line_total = base + gst_amount

        taxable = _q(taxable)
        gst_amount = _q(gst_amount)
        line_total = _q(line_total)
        eff_disc_q = _q(eff_disc)

        if place_of_supply == SUPPLY_INTER:
            igst, cgst, sgst = gst_amount, ZERO, ZERO
        else:
            cgst = _q(gst_amount / 2)
            sgst = gst_amount - cgst  # keep cgst + sgst == gst_amount exactly
            igst = ZERO

        result.lines.append(
            ComputedLine(
                taxable_value=taxable, cgst=cgst, sgst=sgst, igst=igst,
                gst_amount=gst_amount, discount=eff_disc_q, line_total=line_total,
            )
        )
        result.total_taxable += taxable
        result.total_discount += eff_disc_q
        result.total_cgst += cgst
        result.total_sgst += sgst
        result.total_igst += igst
        result.total_gst += gst_amount
        result.grand_total += line_total

    return result
