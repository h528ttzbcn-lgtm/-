"""Writes the research report and the amazon_auto_listing-compatible listing sheet."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import Candidate
from .settings import ResearchSettings

REPORT_FIELDS = [
    "status",
    "reasons",
    "source",
    "shop_name",
    "shop_id",
    "title",
    "jan",
    "source_price",
    "shipping_cost",
    "points_value",
    "extra_costs",
    "total_cost",
    "asin",
    "amazon_title",
    "brand",
    "sales_rank",
    "sales_rank_category",
    "buybox_price",
    "lowest_price",
    "offer_count",
    "sell_price",
    "amazon_fees",
    "profit",
    "roi_pct",
    "margin_pct",
    "source_url",
    "amazon_url",
]

# Same columns amazon_auto_listing's `list` command reads.
LISTING_FIELDS = ["sku", "asin", "price", "quantity", "condition_type", "product_type", "currency", "fulfillment_channel"]


def _r(value, digits=0):
    return "" if value is None else round(value, digits) if digits else round(value)


def _report_row(c: Candidate) -> dict:
    p, o, prod = c.profit, c.offers, c.product
    return {
        "status": c.status,
        "reasons": " / ".join(c.reasons),
        "source": c.item.source,
        "shop_name": c.item.shop_name,
        "shop_id": c.item.shop_id,
        "title": c.item.title,
        "jan": c.item.jan or "",
        "source_price": _r(c.item.price),
        "shipping_cost": _r(p.shipping_cost) if p else _r(c.item.shipping_cost),
        "points_value": _r(p.points_value) if p else "",
        "extra_costs": _r(p.extra_costs) if p else "",
        "total_cost": _r(p.total_cost) if p else "",
        "asin": prod.asin if prod else "",
        "amazon_title": prod.title if prod else "",
        "brand": prod.brand if prod else "",
        "sales_rank": prod.sales_rank if prod and prod.sales_rank is not None else "",
        "sales_rank_category": prod.sales_rank_category if prod else "",
        "buybox_price": _r(o.buybox_price) if o else "",
        "lowest_price": _r(o.lowest_price) if o else "",
        "offer_count": o.offer_count if o else "",
        "sell_price": _r(p.sell_price) if p else "",
        "amazon_fees": _r(p.amazon_fees) if p else "",
        "profit": _r(p.profit) if p else "",
        "roi_pct": _r(p.roi * 100, 1) if p and p.roi is not None else "",
        "margin_pct": _r(p.margin_rate * 100, 1) if p and p.margin_rate is not None else "",
        "source_url": c.item.url,
        "amazon_url": f"https://www.amazon.co.jp/dp/{prod.asin}" if prod else "",
    }


def _sort_key(c: Candidate):
    # OK rows first, then by profit (highest first); rows without profit last.
    return (not c.is_ok, -(c.profit.profit if c.profit else float("-inf")))


def write_report(candidates: list[Candidate], output_dir: str | Path = "output", timestamp: str | None = None) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"research_report_{timestamp}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for c in sorted(candidates, key=_sort_key):
            writer.writerow(_report_row(c))
    return path


def build_listing_rows(candidates: list[Candidate], settings: ResearchSettings) -> list[dict]:
    rows, seen = [], set()
    for c in sorted(candidates, key=_sort_key):
        if not c.is_ok or c.product.asin in seen:
            continue
        seen.add(c.product.asin)
        rows.append(
            {
                "sku": f"{settings.sku_prefix}{c.product.asin}",
                "asin": c.product.asin,
                "price": int(round(c.profit.sell_price)),
                "quantity": settings.listing_quantity,
                "condition_type": settings.condition_type,
                "product_type": c.product.product_type,
                "currency": "JPY",
                "fulfillment_channel": settings.fulfillment_channel,
            }
        )
    return rows


def write_listing_sheet(
    candidates: list[Candidate],
    settings: ResearchSettings,
    output_dir: str | Path = "output",
    timestamp: str | None = None,
) -> Path | None:
    """Writes profitable items as an amazon_auto_listing input CSV. None if there are none."""
    rows = build_listing_rows(candidates, settings)
    if not rows:
        return None
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"listing_candidates_{timestamp}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LISTING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path
