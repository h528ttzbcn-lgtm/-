"""Yahoo!ショッピング 商品検索API (v3 itemSearch) client. Official API only — no scraping.

Unlike Rakuten, v3 returns the JAN code directly (`janCode`), which makes
matching against Amazon much more reliable.
Docs: https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html
"""
from __future__ import annotations

import logging
import time

import requests

from ..config import YahooConfig
from ..jan import normalize_jan
from ..models import SearchQuery, SourceItem

logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 50  # API maximum
MAX_OFFSET = 1000  # start + results must stay within this


class YahooApiError(RuntimeError):
    pass


def parse_item(raw: dict) -> SourceItem:
    seller = raw.get("seller") or {}
    shipping = raw.get("shipping") or {}
    point = raw.get("point") or {}
    return SourceItem(
        source="yahoo",
        shop_id=seller.get("sellerId", ""),
        shop_name=seller.get("name", ""),
        item_code=raw.get("code", ""),
        title=raw.get("name", ""),
        url=raw.get("url", ""),
        price=float(raw.get("price") or 0),
        # shipping.code: 2 = 送料無料. 1 (設定なし) / 3 (条件付き送料無料) are
        # treated as unknown so the configured fallback cost is applied.
        shipping_cost=0.0 if int(shipping.get("code") or 0) == 2 else None,
        points=float(point.get("amount") or 0),
        jan=normalize_jan(raw.get("janCode")),
        in_stock=bool(raw.get("inStock", True)),
        condition=raw.get("condition") or "new",
    )


class YahooClient:
    def __init__(self, config: YahooConfig, throttle_seconds: float = 1.0, session: requests.Session | None = None):
        self.config = config
        self.throttle_seconds = throttle_seconds
        self.session = session or requests.Session()

    def _params(self, query: SearchQuery, page: int) -> dict:
        params = {
            "appid": self.config.client_id,
            "query": query.keyword,
            "results": RESULTS_PER_PAGE,
            "start": (page - 1) * RESULTS_PER_PAGE + 1,
            "in_stock": "true",
            "condition": "new",  # 新品のみ
        }
        if query.shop:
            params["seller_id"] = query.shop
        if query.min_price is not None:
            params["price_from"] = query.min_price
        if query.max_price is not None:
            params["price_to"] = query.max_price
        if query.sort:
            params["sort"] = query.sort
        return params

    def _get(self, params: dict) -> dict:
        response = self.session.get(self.config.endpoint, params=params, timeout=15)
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code != 200:
            error = body.get("Error") or {}
            detail = error.get("Message") if isinstance(error, dict) else None
            raise YahooApiError(f"Yahoo!API エラー HTTP {response.status_code}: {detail or response.text[:200]}")
        return body

    def search(self, query: SearchQuery) -> list[SourceItem]:
        if not self.config.is_complete():
            raise YahooApiError("Yahoo!APIの認証情報が不足しています (.env の YAHOO_CLIENT_ID)。")

        items: list[SourceItem] = []
        for page in range(1, query.pages + 1):
            params = self._params(query, page)
            if params["start"] + RESULTS_PER_PAGE - 1 > MAX_OFFSET:
                break
            body = self._get(params)
            hits = body.get("hits") or []
            items.extend(parse_item(h) for h in hits)

            total = int(body.get("totalResultsAvailable") or 0)
            if not hits or params["start"] + len(hits) > total:
                break
            time.sleep(self.throttle_seconds)
        logger.info("Yahoo: keyword=%r shop=%r -> %d件", query.keyword, query.shop, len(items))
        return items
