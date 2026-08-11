"""Core profit-margin math for a single Product under a given FeeProfile.

Also computes a recommended selling price for a target profit margin, and
flags whether the current price should be raised (値上げ) or lowered
(値下げ) to reach it — the repricing half of "利益計算して値上げや値下げする".
"""
from __future__ import annotations

from dataclasses import dataclass

from .fee_profile import FeeProfile
from .models import Product

DEFAULT_PRICE_TOLERANCE_PCT = 0.02  # within +-2% of current price -> "維持" (no change)


@dataclass
class ProfitResult:
    product_name: str
    category: str
    cost_price: float
    selling_price: float
    quantity: int

    commission_fee: float
    transaction_fee: float
    service_fee: float
    fixed_fee: float
    shipping_cost: float
    other_fixed_cost: float
    export_tax_refund: float
    total_fees: float

    profit_per_unit: float
    profit_total: float
    margin_rate: float | None  # profit_per_unit / selling_price
    roi: float | None  # profit_per_unit / cost_price
    break_even_price: float | None  # minimum selling price for profit == 0

    target_margin_rate: float | None
    recommended_price: float | None  # selling price needed to hit target_margin_rate
    price_diff: float | None  # recommended_price - selling_price
    price_action: str  # "値上げ推奨" | "値下げ推奨" | "維持" | "目標未設定" | "目標利益率が達成不可"

    is_profitable: bool


def _price_for_margin(fixed_and_cost: float, rate_sum: float, margin_rate: float) -> float | None:
    """Selling price P such that: P*(1-rate_sum) - fixed_and_cost == margin_rate * P.

    Returns None if the target margin plus fee rate leaves no room (>=100%
    of the price would be consumed by fees + margin).
    """
    denom = 1 - rate_sum - margin_rate
    if denom <= 0:
        return None
    return fixed_and_cost / denom


def calculate_profit(
    product: Product,
    fee_profile: FeeProfile,
    price_tolerance_pct: float = DEFAULT_PRICE_TOLERANCE_PCT,
) -> ProfitResult:
    commission_fee = product.selling_price * fee_profile.commission_rate_for(product.category)
    transaction_fee = product.selling_price * fee_profile.transaction_fee_rate
    service_fee = product.selling_price * fee_profile.service_fee_rate
    fixed_fee = fee_profile.fixed_fee_per_order

    total_fees = (
        commission_fee
        + transaction_fee
        + service_fee
        + fixed_fee
        + product.shipping_cost
        + product.other_fixed_cost
    )

    # export_tax_refund is money that comes back to you, so it offsets cost.
    profit_per_unit = product.selling_price - product.cost_price - total_fees + product.export_tax_refund
    profit_total = profit_per_unit * product.quantity

    margin_rate = profit_per_unit / product.selling_price if product.selling_price else None
    roi = profit_per_unit / product.cost_price if product.cost_price else None

    rate_sum = fee_profile.total_rate_for(product.category)
    fixed_and_cost = (
        fixed_fee
        + product.shipping_cost
        + product.other_fixed_cost
        + product.cost_price
        - product.export_tax_refund
    )
    break_even_price = _price_for_margin(fixed_and_cost, rate_sum, 0.0)

    target_margin_rate = (
        product.target_margin_rate if product.target_margin_rate is not None else fee_profile.default_target_margin_rate
    )

    recommended_price: float | None = None
    price_diff: float | None = None
    price_action = "目標未設定"

    if target_margin_rate and target_margin_rate > 0:
        recommended_price = _price_for_margin(fixed_and_cost, rate_sum, target_margin_rate)
        if recommended_price is None:
            price_action = "目標利益率が達成不可(手数料率が高すぎます)"
        else:
            price_diff = recommended_price - product.selling_price
            tolerance_abs = product.selling_price * price_tolerance_pct
            if abs(price_diff) <= tolerance_abs:
                price_action = "維持"
            elif price_diff > 0:
                price_action = "値上げ推奨"
            else:
                price_action = "値下げ推奨"

    return ProfitResult(
        product_name=product.product_name,
        category=product.category,
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        quantity=product.quantity,
        commission_fee=commission_fee,
        transaction_fee=transaction_fee,
        service_fee=service_fee,
        fixed_fee=fixed_fee,
        shipping_cost=product.shipping_cost,
        other_fixed_cost=product.other_fixed_cost,
        export_tax_refund=product.export_tax_refund,
        total_fees=total_fees,
        profit_per_unit=profit_per_unit,
        profit_total=profit_total,
        margin_rate=margin_rate,
        roi=roi,
        break_even_price=break_even_price,
        target_margin_rate=target_margin_rate if target_margin_rate else None,
        recommended_price=recommended_price,
        price_diff=price_diff,
        price_action=price_action,
        is_profitable=profit_per_unit > 0,
    )


def calculate_all(
    products: list[Product],
    fee_profile: FeeProfile,
    price_tolerance_pct: float = DEFAULT_PRICE_TOLERANCE_PCT,
) -> list[ProfitResult]:
    return [calculate_profit(p, fee_profile, price_tolerance_pct) for p in products]
