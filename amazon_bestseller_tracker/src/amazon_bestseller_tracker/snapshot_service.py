"""Orchestrates: load watchlist -> fetch current snapshot per ASIN via SP-API
(+ optional Keepa stats) -> diff against the last recorded snapshot -> append
to the history log -> return rows for reporting.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import TrackerConfig
from .history_store import append_snapshot, latest_by_asin, load_history
from .keepa_client import KeepaClient, KeepaClientError
from .models import WatchAsin
from .sp_client import CredentialsMissingError, SpApiClient

logger = logging.getLogger(__name__)


@dataclass
class BestsellerRow:
    asin: str
    memo: str = ""
    title: str = ""
    brand: str = ""
    category: str = ""
    image_url: str | None = None
    current_rank: int | None = None
    previous_rank: int | None = None
    rank_delta: int | None = None
    current_price: float | None = None
    previous_price: float | None = None
    price_delta: float | None = None
    currency: str = ""
    keepa_avg_price: float | None = None
    keepa_avg_rank: float | None = None
    checked_at: str = ""
    status: str = "ok"  # "ok" | "dry-run" | "error"
    detail: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_snapshot(
    watch_items: list[WatchAsin],
    config: TrackerConfig,
    history_path: str,
    dry_run: bool = True,
    keepa_stats_days: int = 30,
) -> list[BestsellerRow]:
    """In dry-run mode no network calls are made at all — only the last
    recorded history entry (if any) is shown, which lets you validate the
    watchlist and history file before you have real credentials.
    """
    previous = latest_by_asin(load_history(history_path))

    if dry_run:
        return [
            BestsellerRow(
                asin=item.asin,
                memo=item.memo,
                previous_rank=previous.get(item.asin, {}).get("current_rank"),
                previous_price=previous.get(item.asin, {}).get("current_price"),
                checked_at=_now_iso(),
                status="dry-run",
                detail="APIは呼び出していません(--no-dry-runで実行してください)",
            )
            for item in watch_items
        ]

    if not config.is_complete():
        raise SystemExit(
            "SP-API 認証情報が不足しています。.env を設定するか --dry-run で実行してください。"
        )

    client = SpApiClient(config)
    keepa_client = KeepaClient(config.keepa_api_key, config.keepa_domain) if config.keepa_api_key else None

    rows: list[BestsellerRow] = []
    for item in watch_items:
        prev = previous.get(item.asin, {})
        checked_at = _now_iso()

        try:
            row = _fetch_row(item, prev, client, keepa_client, checked_at, keepa_stats_days)
            append_snapshot(
                {
                    "asin": item.asin,
                    "checked_at": checked_at,
                    "current_rank": row.current_rank,
                    "current_price": row.current_price,
                    "currency": row.currency,
                    "title": row.title,
                    "category": row.category,
                },
                history_path,
            )
        except CredentialsMissingError as exc:
            # No point continuing the loop if credentials are missing at all.
            raise SystemExit(str(exc))
        except Exception as exc:  # noqa: BLE001 - surfaced per-row in the report
            logger.error("snapshot failed asin=%s: %s", item.asin, exc)
            row = BestsellerRow(
                asin=item.asin,
                memo=item.memo,
                previous_rank=prev.get("current_rank"),
                previous_price=prev.get("current_price"),
                checked_at=checked_at,
                status="error",
                detail=str(exc),
            )

        rows.append(row)

    return rows


def _fetch_row(
    item: WatchAsin,
    prev: dict,
    client: SpApiClient,
    keepa_client: KeepaClient | None,
    checked_at: str,
    keepa_stats_days: int,
) -> BestsellerRow:
    snapshot = client.get_catalog_snapshot(item.asin)
    price, currency = client.get_current_price(item.asin)

    keepa_stats: dict = {}
    if keepa_client:
        try:
            keepa_stats = keepa_client.get_stats(item.asin, days=keepa_stats_days)
        except KeepaClientError as exc:
            logger.warning("Keepa lookup failed for %s: %s", item.asin, exc)

    current_rank = snapshot.get("sales_rank")
    previous_rank = prev.get("current_rank")
    rank_delta = current_rank - previous_rank if current_rank is not None and previous_rank is not None else None

    previous_price = prev.get("current_price")
    price_delta = price - previous_price if price is not None and previous_price is not None else None

    return BestsellerRow(
        asin=item.asin,
        memo=item.memo,
        title=snapshot.get("title", ""),
        brand=snapshot.get("brand", ""),
        category=snapshot.get("category", ""),
        image_url=snapshot.get("image_url"),
        current_rank=current_rank,
        previous_rank=previous_rank,
        rank_delta=rank_delta,
        current_price=price,
        previous_price=previous_price,
        price_delta=price_delta,
        currency=currency or "",
        keepa_avg_price=keepa_stats.get("keepa_avg_price"),
        keepa_avg_rank=keepa_stats.get("keepa_avg_rank"),
        checked_at=checked_at,
        status="ok",
    )
