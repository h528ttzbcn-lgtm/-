"""Reads the input CSV/Excel sheet into validated ListingItem objects."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import ListingItem

REQUIRED_COLUMNS = ["sku", "asin", "price", "quantity"]
OPTIONAL_COLUMNS = {
    "condition_type": "new_new",
    "product_type": "PRODUCT",
    "currency": "JPY",
    "fulfillment_channel": "DEFAULT",
}


class SheetValidationError(ValueError):
    pass


def load_listing_sheet(path: str | Path) -> list[ListingItem]:
    """Load a CSV or Excel file and return validated ListingItem rows.

    Raises SheetValidationError (with all problems collected) if the sheet is
    missing required columns, or if individual rows fail validation.
    """
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)

    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SheetValidationError(
            f"入力シートに必須カラムがありません: {missing}. "
            f"必要なカラム: {REQUIRED_COLUMNS} (+ 任意: {list(OPTIONAL_COLUMNS)})"
        )

    for col, default in OPTIONAL_COLUMNS.items():
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default)

    items: list[ListingItem] = []
    row_errors: list[str] = []

    for i, row in df.iterrows():
        try:
            item = ListingItem(
                sku=str(row["sku"]).strip(),
                asin=str(row["asin"]).strip(),
                price=float(row["price"]),
                quantity=int(float(row["quantity"])),
                condition_type=str(row["condition_type"]).strip(),
                product_type=str(row["product_type"]).strip(),
                currency=str(row["currency"]).strip(),
                fulfillment_channel=str(row["fulfillment_channel"]).strip(),
            )
        except (ValueError, TypeError) as exc:
            row_errors.append(f"row {i + 2}: 型変換に失敗しました ({exc})")
            continue

        errors = item.validate()
        if errors:
            row_errors.append(f"row {i + 2} ({item.sku or item.asin}): " + "; ".join(errors))
            continue

        items.append(item)

    if row_errors:
        raise SheetValidationError("入力シートに問題があります:\n" + "\n".join(row_errors))

    return items
