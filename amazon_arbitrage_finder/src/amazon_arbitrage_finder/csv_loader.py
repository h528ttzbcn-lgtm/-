"""Reads the search-plan sheet and the manual source-item sheet."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .jan import normalize_jan
from .models import SearchQuery, SourceItem


class SheetValidationError(ValueError):
    pass


def _read(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    return df.fillna("")


def _require(df: pd.DataFrame, required: list[str], path) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SheetValidationError(f"{path}: 必須カラムがありません: {missing}")


def _opt_int(value: str) -> int | None:
    value = str(value).strip().replace(",", "")
    return int(float(value)) if value else None


def _opt_float(value: str) -> float | None:
    value = str(value).strip().replace(",", "")
    return float(value) if value else None


def load_queries(path: str | Path) -> list[SearchQuery]:
    """Columns: source, keyword, shop, min_price, max_price, pages, sort (only `source` is required)."""
    df = _read(path)
    _require(df, ["source"], path)

    queries: list[SearchQuery] = []
    errors: list[str] = []
    for idx, row in df.iterrows():
        line = idx + 2  # header is line 1
        try:
            query = SearchQuery(
                source=row.get("source", "").strip().lower(),
                keyword=row.get("keyword", "").strip(),
                shop=row.get("shop", "").strip(),
                min_price=_opt_int(row.get("min_price", "")),
                max_price=_opt_int(row.get("max_price", "")),
                pages=_opt_int(row.get("pages", "")) or 1,
                sort=row.get("sort", "").strip(),
            )
        except ValueError as exc:
            errors.append(f"{line}行目: 数値に変換できません ({exc})")
            continue
        problems = query.validate()
        if problems:
            errors.append(f"{line}行目: " + "; ".join(problems))
            continue
        queries.append(query)

    if errors:
        raise SheetValidationError("検索条件シートにエラーがあります:\n" + "\n".join(errors))
    return queries


def load_manual_items(path: str | Path) -> list[SourceItem]:
    """Items entered by hand (e.g. from a 家電量販店 site without an API, such as its own EC site).

    Columns: jan, price (required); title, shop_name, url, shipping_cost, points (optional).
    """
    df = _read(path)
    _require(df, ["jan", "price"], path)

    items: list[SourceItem] = []
    errors: list[str] = []
    for idx, row in df.iterrows():
        line = idx + 2
        jan = normalize_jan(row["jan"])
        if not jan:
            errors.append(f"{line}行目: JAN '{row['jan']}' が不正です(13桁・チェックディジットを確認)")
            continue
        try:
            price = _opt_float(row["price"])
            shipping = _opt_float(row.get("shipping_cost", ""))
            points = _opt_float(row.get("points", "")) or 0.0
        except ValueError as exc:
            errors.append(f"{line}行目: 数値に変換できません ({exc})")
            continue
        if not price or price <= 0:
            errors.append(f"{line}行目: price は0より大きい数値が必要です")
            continue
        items.append(
            SourceItem(
                source="manual",
                shop_id=row.get("shop_name", ""),
                shop_name=row.get("shop_name", ""),
                item_code="",
                title=row.get("title", ""),
                url=row.get("url", ""),
                price=price,
                shipping_cost=shipping if shipping is not None else 0.0,
                points=points,
                jan=jan,
            )
        )

    if errors:
        raise SheetValidationError("仕入れ商品シートにエラーがあります:\n" + "\n".join(errors))
    return items
