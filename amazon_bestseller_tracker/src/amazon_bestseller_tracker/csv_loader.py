"""Reads the input CSV/Excel watchlist into validated WatchAsin objects."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import WatchAsin

REQUIRED_COLUMNS = ["asin"]
OPTIONAL_COLUMNS = {
    "memo": "",
    "category_hint": "",
}


class SheetValidationError(ValueError):
    pass


def load_watchlist(path: str | Path) -> list[WatchAsin]:
    """Load a CSV or Excel file and return validated WatchAsin rows.

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

    items: list[WatchAsin] = []
    row_errors: list[str] = []

    for i, row in df.iterrows():
        item = WatchAsin(
            asin=str(row["asin"]).strip(),
            memo=str(row["memo"]).strip(),
            category_hint=str(row["category_hint"]).strip(),
        )

        errors = item.validate()
        if errors:
            row_errors.append(f"row {i + 2} ({item.asin}): " + "; ".join(errors))
            continue

        items.append(item)

    if row_errors:
        raise SheetValidationError("入力シートに問題があります:\n" + "\n".join(row_errors))

    return items
