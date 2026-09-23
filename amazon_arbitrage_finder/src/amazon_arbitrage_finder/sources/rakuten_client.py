"""楽天市場 商品検索API (IchibaItem/Search) client. Official API only — no scraping.

Rakuten renewed its Web Service in 2026: the endpoint moved to
openapi.rakuten.co.jp, `accessKey` became mandatory alongside
`applicationId`, and requests must carry the Referer of the website
registered for the app. The version segment of the endpoint (e.g. 20260701)
is bumped from time to time, so it is configurable via RAKUTEN_ENDPOINT.
Docs: https://webservice.rakuten.co.jp/documentation/ichiba-item-search
"""
from __future__ import annotations

import logging
import math
import time

import requests

from ..config import RakutenConfig
from ..jan import extract_jan
from ..models import SearchQuery, SourceItem

logger = logging.getLogger(__name__)

HITS_PER_PAGE = 30  # API maximum
MAX_PAGE = 100  # API maximum


class RakutenApiError(RuntimeError):
    pass


def rakuten_points(price: float, point_rate: float) -> float:
    """楽天市場のショップ付与ポイント: 税抜価格 × 倍率 × 1%(端数切り捨て)."""
    tax_excluded = math.floor(price / 1.1)
    return float(math.floor(tax_excluded * (point_rate or 1) / 100))


def parse_item(raw: dict) -> SourceItem:
    """Convert one API item (formatVersion=2 shape) into a SourceItem."""
    price = float(raw.get("itemPrice") or 0)
    return SourceItem(
        source="rakuten",
        shop_id=raw.get("shopCode", ""),
        shop_name=raw.get("shopName", ""),
        item_code=raw.get("itemCode", ""),
        title=raw.get("itemName", ""),
        url=raw.get("itemUrl", ""),
        price=price,
        # postageFlag: 0 = 送料込み, 1 = 送料別 (amount not returned by the API)
        shipping_cost=0.0 if int(raw.get("postageFlag") or 0) == 0 else None,
        points=rakuten_points(price, float(raw.get("pointRate") or 1)),
        jan=extract_jan(raw.get("itemName"), raw.get("itemCaption")),
        in_stock=int(raw.get("availability", 1) or 0) == 1,
    )


class RakutenClient:
    def __init__(self, config: RakutenConfig, throttle_seconds: float = 1.0, session: requests.Session | None = None):
        self.config = config
        self.throttle_seconds = throttle_seconds
        self.session = session or requests.Session()

    def _params(self, query: SearchQuery, page: int) -> dict:
        params = {
            "applicationId": self.config.application_id,
            "accessKey": self.config.access_key,
            "format": "json",
            "formatVersion": 2,
            "hits": HITS_PER_PAGE,
            "page": page,
            "availability": 1,
        }
        if query.keyword:
            params["keyword"] = query.keyword
        if query.shop:
            params["shopCode"] = query.shop
        if query.min_price is not None:
            params["minPrice"] = query.min_price
        if query.max_price is not None:
            params["maxPrice"] = query.max_price
        if query.sort:
            params["sort"] = query.sort
        return params

    def _get(self, params: dict) -> dict:
        headers = {"Referer": self.config.referer} if self.config.referer else {}
        response = self.session.get(self.config.endpoint, params=params, headers=headers, timeout=15)
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code != 200:
            detail = body.get("error_description") or body.get("error") or response.text[:200]
            raise RakutenApiError(f"楽天API エラー HTTP {response.status_code}: {detail}")
        return body

    def search(self, query: SearchQuery) -> list[SourceItem]:
        if not self.config.is_complete():
            raise RakutenApiError(
                "楽天APIの認証情報が不足しています (.env の RAKUTEN_APPLICATION_ID / RAKUTEN_ACCESS_KEY)。"
            )

        items: list[SourceItem] = []
        for page in range(1, min(query.pages, MAX_PAGE) + 1):
            body = self._get(self._params(query, page))
            raw_items = body.get("Items") or body.get("items") or []
            # formatVersion=1 wraps each entry as {"Item": {...}}
            items.extend(parse_item(r.get("Item", r)) for r in raw_items)

            page_count = int(body.get("pageCount") or 0)
            if page >= page_count:
                break
            time.sleep(self.throttle_seconds)
        logger.info("楽天: keyword=%r shop=%r -> %d件", query.keyword, query.shop, len(items))
        return items
