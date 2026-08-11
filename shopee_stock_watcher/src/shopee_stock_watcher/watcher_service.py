"""Orchestrates: load watchlist -> diff vs last state -> unlist/relist on
Shopee for changed items -> save new state -> report.
"""
from __future__ import annotations

import logging

from .config import ShopeeConfig
from .diff_engine import compute_transitions, next_state
from .models import WatchItem
from .reporter import ActionResult
from .shopee_client import ShopeeApiError, ShopeeClient
from .state_store import load_state, save_state

logger = logging.getLogger(__name__)


def run_watch(
    items: list[WatchItem],
    config: ShopeeConfig,
    state_path: str,
    dry_run: bool = True,
    auto_relist: bool = False,
) -> list[ActionResult]:
    previous_state = load_state(state_path)
    transitions = compute_transitions(items, previous_state, auto_relist=auto_relist)

    client = ShopeeClient(config) if not dry_run else None

    delist_ids = [t.item.shopee_item_id for t in transitions if t.action == "delist"]
    relist_ids = [t.item.shopee_item_id for t in transitions if t.action == "relist"]

    delist_response = None
    relist_response = None

    if not dry_run:
        if not config.is_complete():
            raise SystemExit(
                "Shopee API 認証情報が不足しています。.env を設定するか --dry-run で実行してください。"
            )
        try:
            if delist_ids:
                delist_response = client.unlist_items(delist_ids, unlist=True)
            if relist_ids:
                relist_response = client.unlist_items(relist_ids, unlist=False)
        except ShopeeApiError as exc:
            logger.error("Shopee API call failed: %s", exc)
            # Fall through so we still produce a report + do NOT save state,
            # since we don't know which items actually got updated.
            results = [
                ActionResult(
                    shopee_item_id=t.item.shopee_item_id,
                    product_name=t.item.product_name,
                    source_asin=t.item.source_asin,
                    previous_status=t.previous_status or "",
                    current_status=t.item.current_status,
                    action=t.action,
                    result="error" if t.action != "none" else "skipped",
                    detail=str(exc) if t.action != "none" else "",
                )
                for t in transitions
            ]
            return results

    results = []
    for t in transitions:
        if t.action == "none":
            results.append(
                ActionResult(
                    shopee_item_id=t.item.shopee_item_id,
                    product_name=t.item.product_name,
                    source_asin=t.item.source_asin,
                    previous_status=t.previous_status or "",
                    current_status=t.item.current_status,
                    action="none",
                    result="skipped",
                )
            )
            continue

        action_label = f"dry-run-{t.action}" if dry_run else t.action
        results.append(
            ActionResult(
                shopee_item_id=t.item.shopee_item_id,
                product_name=t.item.product_name,
                source_asin=t.item.source_asin,
                previous_status=t.previous_status or "",
                current_status=t.item.current_status,
                action=action_label,
                result="ok",
                detail="API未呼び出し(dry-run)" if dry_run else "",
            )
        )

    # Only persist state once we're confident about what happened (dry-run
    # always safe to persist too — it reflects observed reality, not actions).
    save_state(next_state(items, previous_state), state_path)

    return results
