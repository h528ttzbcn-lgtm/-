"""Builds the SP-API Listings Items `attributes` payload for a ListingItem."""
from __future__ import annotations

import json
from pathlib import Path
from string import Template

from .models import ListingItem

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template_text(product_type: str) -> str:
    """Prefer templates/<PRODUCT_TYPE>.json, fall back to templates/generic.json."""
    custom = TEMPLATES_DIR / f"{product_type}.json"
    if custom.exists():
        return custom.read_text(encoding="utf-8")
    return (TEMPLATES_DIR / "generic.json").read_text(encoding="utf-8")


def build_attributes(item: ListingItem, marketplace_id: str) -> dict:
    """Render the item's template with its field values and return a dict
    ready to place under `body["attributes"]` for ListingsItems.put_listings_item.
    """
    template_text = _load_template_text(item.product_type)
    rendered = Template(template_text).safe_substitute(
        asin=item.asin,
        sku=item.sku,
        price=item.price,
        quantity=item.quantity,
        currency=item.currency,
        condition_type=item.condition_type,
        fulfillment_channel=item.fulfillment_channel,
        marketplace_id=marketplace_id,
    )
    attributes = json.loads(rendered)
    attributes.pop("_comment", None)
    return attributes


def build_listing_body(item: ListingItem, marketplace_id: str) -> dict:
    return {
        "productType": item.product_type,
        "requirements": "LISTING",
        "attributes": build_attributes(item, marketplace_id),
    }
