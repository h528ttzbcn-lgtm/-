"""Data models shared across sources, the Amazon lookup and the profit calculation."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchQuery:
    """One row of the search-plan sheet (data/sample_queries.csv).

    source: "rakuten" or "yahoo".
    keyword: free-text search keyword. Required for yahoo; for rakuten it may
        be empty when `shop` is set (lists the whole shop).
    shop: restrict to one store — Rakuten `shopCode` or Yahoo! `seller_id`.
        This is how 家電量販店 (ビックカメラ/ヤマダ/Joshin/コジマ etc.) stores
        are targeted; see README "家電量販店ストアの指定".
    min_price / max_price: price range filter (税込, 円).
    pages: how many result pages to fetch.
    sort: passed through to the API as-is (source-specific syntax).
    """

    source: str
    keyword: str = ""
    shop: str = ""
    min_price: int | None = None
    max_price: int | None = None
    pages: int = 1
    sort: str = ""

    def validate(self) -> list[str]:
        errors = []
        if self.source not in ("rakuten", "yahoo"):
            errors.append(f"source は rakuten / yahoo のいずれかです: '{self.source}'")
        if self.source == "rakuten" and not (self.keyword or self.shop):
            errors.append("rakuten は keyword か shop のどちらかが必要です")
        if self.source == "yahoo" and not self.keyword:
            errors.append("yahoo は keyword が必要です")
        if self.pages < 1:
            errors.append(f"pages は1以上: {self.pages}")
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            errors.append(f"min_price({self.min_price}) > max_price({self.max_price})")
        return errors


@dataclass
class SourceItem:
    """A product offered on a purchase-source site (仕入れ先).

    price: 税込 selling price on the source site.
    shipping_cost: 0 when shipping is included/free, None when it is charged
        separately but the amount is unknown (the research settings then apply
        `unknown_shipping_cost`).
    points: points granted by the source site itself, in points (1pt = 1円
        before `point_value_rate` is applied).
    jan: 13-digit JAN/EAN if known. Items without it can't be matched to
        Amazon reliably and are skipped.
    condition: "new" or "used" as reported by the source ("new" when the
        source doesn't say — Rakuten has no such field, so used items there
        are caught by title keywords instead).
    """

    source: str
    shop_id: str
    shop_name: str
    item_code: str
    title: str
    url: str
    price: float
    shipping_cost: float | None = 0.0
    points: float = 0.0
    jan: str | None = None
    in_stock: bool = True
    condition: str = "new"


@dataclass
class AmazonProduct:
    asin: str
    jan: str
    title: str = ""
    brand: str = ""
    product_type: str = "PRODUCT"
    sales_rank: int | None = None
    sales_rank_category: str = ""


@dataclass
class AmazonOffers:
    buybox_price: float | None = None
    lowest_price: float | None = None
    offer_count: int = 0


@dataclass
class ProfitBreakdown:
    sell_price: float
    amazon_fees: float
    purchase_price: float
    shipping_cost: float
    points_value: float
    extra_costs: float
    total_cost: float
    profit: float
    roi: float | None
    margin_rate: float | None


@dataclass
class Candidate:
    """One source item after the Amazon lookup, with the reason it was kept or dropped."""

    item: SourceItem
    product: AmazonProduct | None = None
    offers: AmazonOffers | None = None
    profit: ProfitBreakdown | None = None
    status: str = "pending"  # "OK" when it passes every filter
    reasons: list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return self.status == "OK"

    def reject(self, status: str, reason: str = "") -> "Candidate":
        self.status = status
        if reason:
            self.reasons.append(reason)
        return self
