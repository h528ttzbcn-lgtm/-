"""Core profit-margin math for a single Product under a given FeeProfile."""
from __future__ import annotations

from dataclasses import dataclass

from .fee_profile import FeeProfile
from .models import Product


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
    total_fees: float

    profit_per_unit: float
    profit_total: float
    margin_rate: float | None  # profit_per_unit / selling_price
    roi: float | None  # profit_per_unit / cost_price
    break_even_price: float | None  # minimum selling price for profit == 0

    is_profitable: bool


def calculate_profit(product: Product, fee_profile: FeeProfile) -> ProfitResult:
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

    profit_per_unit = product.selling_price - product.cost_price - total_fees
    profit_total = profit_per_unit * product.quantity

    margin_rate = profit_per_unit / product.selling_price if product.selling_price else None
    roi = profit_per_unit / product.cost_price if product.cost_price else None

    rate_sum = fee_profile.total_rate_for(product.category)
    fixed_costs = fixed_fee + product.shipping_cost + product.other_fixed_cost + product.cost_price
    break_even_price = fixed_costs / (1 - rate_sum) if rate_sum < 1 else None

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
        total_fees=total_fees,
        profit_per_unit=profit_per_unit,
        profit_total=profit_total,
        margin_rate=margin_rate,
        roi=roi,
        break_even_price=break_even_price,
        is_profitable=profit_per_unit > 0,
    )


def calculate_all(products: list[Product], fee_profile: FeeProfile) -> list[ProfitResult]:
    return [calculate_profit(p, fee_profile) for p in products]
