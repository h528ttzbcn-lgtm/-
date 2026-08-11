"""Reads the watchlist CSV/Excel sheet into validated WatchItem objects.

Each run, you update `current_status` (in_stock / out_of_stock) for every row
based on what you observe on Amazon.co.jp before running the tool. This tool
does not fetch that status itself.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import WatchItem

REQUIRED_COLUMNS = ["shopee_item_id", "product_name", "current_status"]
OPTIONAL_COLUMNS = {
    "shopee_sku": "",
    "source_asin": "",
    "source_price": None,
}


class SheetValidationError(ValueError):
    pass


def load_watchlist(path: str | Path) -> list[WatchItem]:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)

    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SheetValidationError(
            f"ウォッチリストに必須カラムがありません: {missing}. "
            f"必要なカラム: {REQUIRED_COLUMNS} (+ 任意: {list(OPTIONAL_COLUMNS)})"
        )

    for col, default in OPTIONAL_COLUMNS.items():
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default)

    items: list[WatchItem] = []
    row_errors: list[str] = []

    for i, row in df.iterrows():
        try:
            source_price_raw = row["source_price"]
            source_price = (
                None if source_price_raw is None or pd.isna(source_price_raw) or source_price_raw == ""
                else float(source_price_raw)
            )
            item = WatchItem(
                shopee_item_id=int(float(row["shopee_item_id"])),
                product_name=str(row["product_name"]).strip(),
                current_status=str(row["current_status"]).strip(),
                shopee_sku=str(row["shopee_sku"]).strip(),
                source_asin=str(row["source_asin"]).strip(),
                source_price=source_price,
            )
        except (ValueError, TypeError) as exc:
            row_errors.append(f"row {i + 2}: 型変換に失敗しました ({exc})")
            continue

        errors = item.validate()
        if errors:
            row_errors.append(f"row {i + 2} ({item.product_name or item.shopee_item_id}): " + "; ".join(errors))
            continue

        items.append(item)

    if row_errors:
        raise SheetValidationError("ウォッチリストに問題があります:\n" + "\n".join(row_errors))

    return items
