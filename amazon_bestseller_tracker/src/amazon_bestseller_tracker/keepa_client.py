"""Optional wrapper around the `keepa` PyPI package for Keepa-style
price/sales-rank statistics.

Keepa is an official third-party data service you subscribe to directly
(https://keepa.com/#!api) — this is not scraping Amazon and requires your
own KEEPA_API_KEY. It's the practical way to get the kind of long-running
price/rank *history* Amazon itself does not expose via any public API; SP-API
only ever returns the current snapshot (see sp_client.py).

This integration is entirely optional: if KEEPA_API_KEY is unset, the tool
still works using SP-API alone (current rank/price + your own accumulated
history from repeated runs).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Keepa CSV history "type" indices (see https://keepa.com/#!discuss/t/product-object/116).
# Only the two we surface here; Keepa defines many more (Amazon price, used,
# buy box, offer counts, rating, ...).
CSV_TYPE_NEW = 1
CSV_TYPE_SALES_RANK = 3

# Keepa reports most price types in the marketplace's smallest currency unit
# (e.g. cents) *100, except JP where prices are already whole yen.
_NO_MINOR_UNIT_DOMAINS = {"JP"}


class KeepaClientError(RuntimeError):
    pass


class KeepaClient:
    """Lazily imports the `keepa` package so it's only required if you
    actually set KEEPA_API_KEY.
    """

    def __init__(self, api_key: str, domain: str = "JP"):
        self.api_key = api_key
        self.domain = domain
        self._api = None

    def _client(self):
        if self._api is None:
            try:
                import keepa
            except ImportError as exc:
                raise KeepaClientError(
                    "keepaパッケージが未インストールです。`pip install keepa` "
                    "(または `pip install -e '.[keepa]'`) を実行してください。"
                ) from exc
            self._api = keepa.Keepa(self.api_key)
        return self._api

    def _to_currency_units(self, raw: float | None) -> float | None:
        if raw is None:
            return None
        if self.domain in _NO_MINOR_UNIT_DOMAINS:
            return float(raw)
        return raw / 100.0

    def get_stats(self, asin: str, days: int = 30) -> dict:
        """Trailing-`days` average and current price/sales-rank, as tracked by
        Keepa's own long-running history for this ASIN.

        Returns {} if Keepa has no data for this ASIN/marketplace (e.g. it's
        never been observed by Keepa's crawler) rather than raising, since
        this is a "nice to have" enrichment on top of the SP-API snapshot.
        """
        api = self._client()
        try:
            products = api.query(asin, domain=self.domain, stats=days, history=False)
        except Exception as exc:  # noqa: BLE001 - surfaced as a warning, not fatal
            raise KeepaClientError(f"Keepa API呼び出しに失敗しました (asin={asin}): {exc}") from exc

        if not products:
            return {}

        return self._parse_stats(products[0], days)

    def _parse_stats(self, product: dict, days: int) -> dict:
        stats = product.get("stats") or {}
        avg = stats.get(f"avg{days}") or []
        current = stats.get("current") or []

        def value(arr, idx):
            if idx >= len(arr):
                return None
            v = arr[idx]
            # Keepa uses -1 (or None) to mean "no data at this point".
            return None if v is None or v < 0 else v

        return {
            "keepa_avg_price": self._to_currency_units(value(avg, CSV_TYPE_NEW)),
            "keepa_avg_rank": value(avg, CSV_TYPE_SALES_RANK),
            "keepa_current_price": self._to_currency_units(value(current, CSV_TYPE_NEW)),
            "keepa_current_rank": value(current, CSV_TYPE_SALES_RANK),
        }
