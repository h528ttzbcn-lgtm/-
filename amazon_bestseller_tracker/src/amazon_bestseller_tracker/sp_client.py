"""Thin wrapper around python-amazon-sp-api for the read-only calls this tool
needs: Catalog Items API (title/brand/category sales-rank/image) and Product
Pricing API (current competitive price).

No scraping of Amazon's Bestsellers pages is done or possible here — Amazon's
official APIs (SP-API, and the retired PA-API BrowseNodeLookup) do not expose
a "top N ASINs in this category" endpoint. This tool instead looks up
whichever ASINs you supply and records their rank/price on each run, so that
running it repeatedly (e.g. via cron) builds up your own Keepa-style history
— see history_store.py / snapshot_service.py.
"""
from __future__ import annotations

import logging

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import TrackerConfig

logger = logging.getLogger(__name__)


class CredentialsMissingError(RuntimeError):
    pass


def _marketplace(config: TrackerConfig):
    from sp_api.base import Marketplaces

    try:
        return getattr(Marketplaces, config.marketplace)
    except AttributeError as exc:
        valid = [m.name for m in Marketplaces]
        raise ValueError(
            f"未知のマーケットプレイス '{config.marketplace}'。有効な値: {valid}"
        ) from exc


def extract_catalog_snapshot(payload: dict) -> dict:
    """Pull title/brand/category-rank/image out of a Catalog Items
    `getCatalogItem` payload (includedData=summaries,salesRanks,images).

    Pure function (no network/SDK dependency) so it can be unit tested with a
    synthetic payload dict.
    """
    summaries = payload.get("summaries") or []
    summary = summaries[0] if summaries else {}

    images = payload.get("images") or []
    image_url = None
    if images and images[0].get("images"):
        image_url = images[0]["images"][0].get("link")

    rank_entry = None
    for sales_rank in payload.get("salesRanks") or []:
        ranks = sales_rank.get("displayGroupRanks") or sales_rank.get("classificationRanks") or []
        if ranks:
            rank_entry = ranks[0]
            break

    return {
        "title": summary.get("itemName", ""),
        "brand": summary.get("brand", ""),
        "category": rank_entry.get("title", "") if rank_entry else "",
        "sales_rank": rank_entry.get("rank") if rank_entry else None,
        "image_url": image_url,
    }


def extract_price(payload: list) -> tuple[float | None, str]:
    """Pull the first competitive landed price out of a Product Pricing API
    `getCompetitivePricingForASINs` payload. Pure function, unit testable.
    """
    for result in payload or []:
        product = result.get("Product") or {}
        competitive_prices = (product.get("CompetitivePricing") or {}).get("CompetitivePrices") or []
        if competitive_prices:
            landed = (competitive_prices[0].get("Price") or {}).get("LandedPrice") or {}
            amount = landed.get("Amount")
            currency = landed.get("CurrencyCode", "")
            return (float(amount) if amount is not None else None), currency

    return None, ""


class SpApiClient:
    """Lazily imports python-amazon-sp-api so --dry-run works without it
    installed against real credentials, and raises a clear error if
    credentials are missing at the moment an actual API call is attempted.
    """

    def __init__(self, config: TrackerConfig):
        self.config = config

    def _require_credentials(self):
        if not self.config.is_complete():
            raise CredentialsMissingError(
                "SP-API 認証情報が不足しています。.env を設定してください "
                "(LWA_APP_ID, LWA_CLIENT_SECRET, SP_API_REFRESH_TOKEN)。"
                " README.md の「SP-API 認証情報の取得手順」を参照してください。"
            )

    @property
    def marketplace_id(self) -> str:
        return _marketplace(self.config).marketplace_id

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(Exception),
    )
    def get_catalog_snapshot(self, asin: str) -> dict:
        """Title・brand・category sales-rank・image for one ASIN, via the
        Catalog Items API `getCatalogItem` operation.
        """
        self._require_credentials()
        from sp_api.api import CatalogItems
        from sp_api.base import SellingApiException

        client = CatalogItems(marketplace=_marketplace(self.config), credentials=self.config.credentials_dict())
        try:
            response = client.get_catalog_item(
                asin,
                marketplaceIds=[self.marketplace_id],
                includedData=["summaries", "salesRanks", "images"],
            )
        except SellingApiException as exc:
            logger.warning("SP-API Catalog Items error for asin=%s: %s", asin, exc)
            raise

        return extract_catalog_snapshot(response.payload)

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(Exception),
    )
    def get_current_price(self, asin: str) -> tuple[float | None, str]:
        """Current lowest landed price for one ASIN, via the Product Pricing
        API `getCompetitivePricingForASINs` operation.
        """
        self._require_credentials()
        from sp_api.api import Products
        from sp_api.base import SellingApiException

        client = Products(marketplace=_marketplace(self.config), credentials=self.config.credentials_dict())
        try:
            response = client.get_competitive_pricing_for_asins(asin_list=[asin])
        except SellingApiException as exc:
            logger.warning("SP-API Product Pricing error for asin=%s: %s", asin, exc)
            raise

        return extract_price(response.payload)
