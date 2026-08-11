"""Data model for a single row of the input listing sheet."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ListingItem:
    """One product to list against an existing ASIN.

    sku: your own seller SKU for this offer (must be unique in your inventory).
    asin: the existing Amazon catalog ASIN you want to sell against ("相乗り出品").
    price: your offer price (numeric, no currency symbol).
    quantity: sellable quantity.
    condition_type: one of Amazon's condition_type enum values, e.g. "new_new",
        "used_like_new", "used_very_good", "used_good", "used_acceptable".
    product_type: the Amazon product type code for this ASIN's category
        (e.g. "LUGGAGE", "GROCERY", "PRODUCT"). Required because the Listings
        Items API validates attributes against a per-product-type schema.
        Look this up once per ASIN via the Catalog Items API or Seller Central
        and cache it in your sheet — see README "product_type について".
    currency: ISO currency code, defaults to JPY.
    fulfillment_channel: "DEFAULT" (self-ship / merchant fulfilled) or "AMAZON_NA"
        style codes for FBA, depending on marketplace. Left as DEFAULT unless
        you override it.
    """

    sku: str
    asin: str
    price: float
    quantity: int
    condition_type: str = "new_new"
    product_type: str = "PRODUCT"
    currency: str = "JPY"
    fulfillment_channel: str = "DEFAULT"

    def validate(self) -> list[str]:
        errors = []
        if not self.sku:
            errors.append("sku is empty")
        if not self.asin or len(self.asin) != 10:
            errors.append(f"asin '{self.asin}' does not look like a valid 10-character ASIN")
        if self.price is None or self.price <= 0:
            errors.append(f"price must be > 0, got {self.price}")
        if self.quantity is None or self.quantity < 0:
            errors.append(f"quantity must be >= 0, got {self.quantity}")
        if not self.product_type:
            errors.append("product_type is empty")
        return errors
