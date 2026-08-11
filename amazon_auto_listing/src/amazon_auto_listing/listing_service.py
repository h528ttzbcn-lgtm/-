"""Orchestrates: load sheet -> build payload -> submit to SP-API -> collect results."""
from __future__ import annotations

import json
import logging
import time

from .attribute_builder import build_listing_body
from .config import SpApiConfig
from .models import ListingItem
from .reporter import ListingResult
from .sp_client import CredentialsMissingError, SpApiClient

logger = logging.getLogger(__name__)


def run_listings(
    items: list[ListingItem],
    config: SpApiConfig,
    dry_run: bool = True,
    throttle_seconds: float = 1.0,
) -> list[ListingResult]:
    """Submit each item as a listing. In dry-run mode no network calls are
    made; the built request body is only logged, which lets you validate the
    input sheet and generated payloads before you have real credentials.
    """
    client = SpApiClient(config)
    results: list[ListingResult] = []

    # marketplace_id is needed to render templates even in dry-run, so fall
    # back to a lookup that doesn't require credentials.
    try:
        marketplace_id = client.marketplace_id
    except ValueError as exc:
        raise SystemExit(str(exc))

    for i, item in enumerate(items):
        body = build_listing_body(item, marketplace_id)

        if dry_run:
            logger.info("[DRY-RUN] sku=%s asin=%s\n%s", item.sku, item.asin, json.dumps(body, ensure_ascii=False, indent=2))
            results.append(ListingResult(sku=item.sku, asin=item.asin, status="dry-run", detail="submitted body only logged"))
            continue

        try:
            payload = client.put_listing(item.sku, body)
            status = payload.get("status", "unknown")
            issues = payload.get("issues", [])
            detail = json.dumps(issues, ensure_ascii=False) if issues else "OK"
            results.append(ListingResult(sku=item.sku, asin=item.asin, status=status or "success", detail=detail))
        except CredentialsMissingError as exc:
            # No point continuing the loop if credentials are missing at all.
            raise SystemExit(str(exc))
        except Exception as exc:  # noqa: BLE001 - surfaced per-row in the report
            logger.error("listing failed sku=%s asin=%s: %s", item.sku, item.asin, exc)
            results.append(ListingResult(sku=item.sku, asin=item.asin, status="error", detail=str(exc)))

        if i < len(items) - 1 and throttle_seconds > 0:
            time.sleep(throttle_seconds)

    return results
