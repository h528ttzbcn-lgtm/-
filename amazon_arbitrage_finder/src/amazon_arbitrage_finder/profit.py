"""Profit math for reselling one source item on Amazon."""
from __future__ import annotations

from .models import AmazonOffers, ProfitBreakdown, SourceItem
from .settings import ResearchSettings


def target_sell_price(offers: AmazonOffers, settings: ResearchSettings) -> float | None:
    """The Amazon price we expect to sell at, or None if there's no reference price."""
    if settings.price_basis == "lowest":
        base = offers.lowest_price or offers.buybox_price
    else:
        base = offers.buybox_price or offers.lowest_price
    if not base:
        return None
    price = base - settings.undercut_yen
    return price if price > 0 else None


def _extra_costs(settings: ResearchSettings) -> float:
    return settings.inbound_shipping_per_unit + settings.packaging_per_unit + settings.other_cost_per_unit


def purchase_cost(item: SourceItem, settings: ResearchSettings) -> tuple[float, float, float]:
    """(shipping_cost, points_value, total purchase cost incl. per-unit extras).

    Points are subtracted because they come back to you, so they effectively
    lower the purchase price.
    """
    shipping = item.shipping_cost if item.shipping_cost is not None else settings.unknown_shipping_cost
    points_value = (item.points + item.price * settings.extra_point_rate_for(item.source)) * settings.point_value_rate
    return shipping, points_value, item.price + shipping - points_value + _extra_costs(settings)


def calculate_profit(
    item: SourceItem, sell_price: float, amazon_fees: float, settings: ResearchSettings
) -> ProfitBreakdown:
    shipping, points_value, total_cost = purchase_cost(item, settings)
    profit = sell_price - amazon_fees - total_cost
    return ProfitBreakdown(
        sell_price=sell_price,
        amazon_fees=amazon_fees,
        purchase_price=item.price,
        shipping_cost=shipping,
        points_value=points_value,
        extra_costs=_extra_costs(settings),
        total_cost=total_cost,
        profit=profit,
        roi=profit / total_cost if total_cost > 0 else None,
        margin_rate=profit / sell_price if sell_price else None,
    )
