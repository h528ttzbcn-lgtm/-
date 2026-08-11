"""Reads the input product sheet (CSV/Excel) into validated Product objects."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import Product

REQUIRED_COLUMNS = ["product_name", "cost_price", "selling_price"]
OPTIONAL_COLUMNS = {
    "quantity": 1,
    "category": "",
    "shipping_cost": 0.0,
    "other_fixed_cost": 0.0,
}


class SheetValidationError(ValueError):
    pass


def load_product_sheet(path: str | Path) -> list[Product]:
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

    products: list[Product] = []
    row_errors: list[str] = []

    for i, row in df.iterrows():
        try:
            product = Product(
                product_name=str(row["product_name"]).strip(),
                cost_price=float(row["cost_price"]),
                selling_price=float(row["selling_price"]),
                quantity=int(float(row["quantity"])),
                category=str(row["category"]).strip(),
                shipping_cost=float(row["shipping_cost"]),
                other_fixed_cost=float(row["other_fixed_cost"]),
            )
        except (ValueError, TypeError) as exc:
            row_errors.append(f"row {i + 2}: 型変換に失敗しました ({exc})")
            continue

        errors = product.validate()
        if errors:
            row_errors.append(f"row {i + 2} ({product.product_name}): " + "; ".join(errors))
            continue

        products.append(product)

    if row_errors:
        raise SheetValidationError("入力シートに問題があります:\n" + "\n".join(row_errors))

    return products
