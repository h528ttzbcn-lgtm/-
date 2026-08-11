"""Writes ProfitResult rows to a timestamped CSV report, worst margin first."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .calculator import ProfitResult

FIELDNAMES = [
    "product_name",
    "category",
    "cost_price",
    "selling_price",
    "quantity",
    "commission_fee",
    "transaction_fee",
    "service_fee",
    "fixed_fee",
    "shipping_cost",
    "other_fixed_cost",
    "total_fees",
    "profit_per_unit",
    "profit_total",
    "margin_rate_pct",
    "roi_pct",
    "break_even_price",
    "is_profitable",
]


def _row(r: ProfitResult) -> dict:
    return {
        "product_name": r.product_name,
        "category": r.category,
        "cost_price": round(r.cost_price, 2),
        "selling_price": round(r.selling_price, 2),
        "quantity": r.quantity,
        "commission_fee": round(r.commission_fee, 2),
        "transaction_fee": round(r.transaction_fee, 2),
        "service_fee": round(r.service_fee, 2),
        "fixed_fee": round(r.fixed_fee, 2),
        "shipping_cost": round(r.shipping_cost, 2),
        "other_fixed_cost": round(r.other_fixed_cost, 2),
        "total_fees": round(r.total_fees, 2),
        "profit_per_unit": round(r.profit_per_unit, 2),
        "profit_total": round(r.profit_total, 2),
        "margin_rate_pct": round(r.margin_rate * 100, 2) if r.margin_rate is not None else "",
        "roi_pct": round(r.roi * 100, 2) if r.roi is not None else "",
        "break_even_price": round(r.break_even_price, 2) if r.break_even_price is not None else "",
        "is_profitable": r.is_profitable,
    }


def write_report(results: list[ProfitResult], output_dir: str | Path = "output") -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"profit_report_{timestamp}.csv"

    # Sort worst margin first so low/negative-profit products are easy to spot.
    sorted_results = sorted(results, key=lambda r: r.margin_rate if r.margin_rate is not None else float("-inf"))

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in sorted_results:
            writer.writerow(_row(r))

    return path
