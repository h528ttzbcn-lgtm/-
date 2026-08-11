"""Data model for a single row of the watchlist sheet."""
from __future__ import annotations

from dataclasses import dataclass

VALID_STATUSES = {"in_stock", "out_of_stock"}


@dataclass
class WatchItem:
    shopee_item_id: int
    product_name: str
    current_status: str  # "in_stock" | "out_of_stock" — you fill this in each time you check Amazon
    shopee_sku: str = ""
    source_asin: str = ""
    source_price: float | None = None

    def validate(self) -> list[str]:
        errors = []
        if not self.shopee_item_id:
            errors.append("shopee_item_id is empty/zero")
        if not self.product_name:
            errors.append("product_name is empty")
        if self.current_status not in VALID_STATUSES:
            errors.append(f"current_status must be one of {sorted(VALID_STATUSES)}, got '{self.current_status}'")
        return errors
