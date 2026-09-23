"""SP-API calls used for research: JAN -> ASIN lookup, offers, fee estimate and
listing restrictions. Read-only — nothing here creates or changes listings.
"""
from __future__ import annotations

import logging
import time

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import SpApiConfig
from .models import AmazonOffers, AmazonProduct

logger = logging.getLogger(__name__)

CATALOG_BATCH_SIZE = 20  # searchCatalogItems accepts up to 20 identifiers

# Minimum seconds between calls, from each operation's SP-API usage plan.
MIN_INTERVAL = {
    "catalog": 0.5,  # searchCatalogItems: 2 req/s
    "offers": 2.0,  # getItemOffers: 0.5 req/s
    "fees": 1.0,  # getMyFeesEstimateForASIN: 1 req/s
    "restrictions": 0.2,  # getListingsRestrictions: 5 req/s
}


class CredentialsMissingError(RuntimeError):
    pass


def _marketplace(config: SpApiConfig):
    from sp_api.base import Marketplaces

    try:
        return getattr(Marketplaces, config.marketplace)
    except AttributeError as exc:
        valid = [m.name for m in Marketplaces]
        raise ValueError(f"未知のマーケットプレイス '{config.marketplace}'。有効な値: {valid}") from exc


def _for_marketplace(entries: list, marketplace_id: str) -> list:
    return [e for e in entries or [] if e.get("marketplaceId") in (None, marketplace_id)]


def parse_catalog_item(raw: dict, requested_jans: set[str], marketplace_id: str) -> list[AmazonProduct]:
    """One catalog item -> one AmazonProduct per requested JAN it carries."""
    jans = set()
    for group in _for_marketplace(raw.get("identifiers"), marketplace_id):
        for ident in group.get("identifiers", []):
            value = ident.get("identifier", "")
            if value in requested_jans:
                jans.add(value)

    summary = next(iter(_for_marketplace(raw.get("summaries"), marketplace_id)), {})
    product_type = next(
        (pt.get("productType") for pt in _for_marketplace(raw.get("productTypes"), marketplace_id)), None
    )

    rank, rank_category = None, ""
    for group in _for_marketplace(raw.get("salesRanks"), marketplace_id):
        ranks = group.get("displayGroupRanks") or group.get("classificationRanks") or []
        if ranks:
            rank, rank_category = ranks[0].get("rank"), ranks[0].get("title", "")
            break

    return [
        AmazonProduct(
            asin=raw.get("asin", ""),
            jan=jan,
            title=summary.get("itemName", ""),
            brand=summary.get("brand") or summary.get("brandName", ""),
            product_type=product_type or "PRODUCT",
            sales_rank=int(rank) if rank is not None else None,
            sales_rank_category=rank_category,
        )
        for jan in sorted(jans)
    ]


def parse_offers(payload: dict) -> AmazonOffers:
    """getItemOffers payload -> buybox / lowest new landed price and offer count."""
    summary = payload.get("Summary") or {}

    def _new(entries):
        return [e for e in entries or [] if str(e.get("condition", "")).lower() == "new"]

    def _amount(entry):
        price = entry.get("LandedPrice") or entry.get("ListingPrice") or {}
        return float(price["Amount"]) if price.get("Amount") is not None else None

    buybox = next((_amount(e) for e in _new(summary.get("BuyBoxPrices"))), None)
    lowest_candidates = [a for a in (_amount(e) for e in _new(summary.get("LowestPrices"))) if a is not None]

    offer_count = summary.get("TotalOfferCount")
    if offer_count is None:
        offer_count = sum(
            int(n.get("OfferCount", 0)) for n in _new(summary.get("NumberOfOffers"))
        )
    return AmazonOffers(
        buybox_price=buybox,
        lowest_price=min(lowest_candidates) if lowest_candidates else None,
        offer_count=int(offer_count or 0),
    )


def parse_fees(payload: dict) -> float:
    result = payload.get("FeesEstimateResult") or {}
    if result.get("Status") not in (None, "Success"):
        error = result.get("Error") or {}
        raise RuntimeError(f"手数料見積もりに失敗: {error.get('Message') or result.get('Status')}")
    return float(result["FeesEstimate"]["TotalFeesEstimate"]["Amount"])


def parse_restrictions(payload: dict) -> list[str]:
    """Empty list means the seller can list this ASIN in the requested condition."""
    messages = []
    for restriction in payload.get("restrictions") or []:
        for reason in restriction.get("reasons") or [{}]:
            messages.append(reason.get("message") or reason.get("reasonCode") or "出品制限あり")
    return messages


class AmazonClient:
    def __init__(self, config: SpApiConfig):
        self.config = config
        self._last_call: dict[str, float] = {}

    def _require_credentials(self):
        if not self.config.is_complete():
            raise CredentialsMissingError(
                "SP-API 認証情報が不足しています。.env を設定してください "
                "(LWA_APP_ID, LWA_CLIENT_SECRET, SP_API_REFRESH_TOKEN, SP_API_SELLER_ID)。"
            )

    def _wait(self, operation: str):
        elapsed = time.monotonic() - self._last_call.get(operation, 0.0)
        if elapsed < MIN_INTERVAL[operation]:
            time.sleep(MIN_INTERVAL[operation] - elapsed)
        self._last_call[operation] = time.monotonic()

    @property
    def marketplace_id(self) -> str:
        return _marketplace(self.config).marketplace_id

    def _kwargs(self) -> dict:
        return {"marketplace": _marketplace(self.config), "credentials": self.config.credentials_dict()}

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
    )
    def _call(self, operation: str, fn, *args, **kwargs):
        self._wait(operation)
        return fn(*args, **kwargs).payload

    def search_by_jans(self, jans: list[str]) -> dict[str, list[AmazonProduct]]:
        """JAN -> matching catalog items (usually 0 or 1; several means variants/sets to double-check)."""
        self._require_credentials()
        from sp_api.api import CatalogItems, CatalogItemsVersion

        client = CatalogItems(version=CatalogItemsVersion.V_2022_04_01, **self._kwargs())
        result: dict[str, list[AmazonProduct]] = {jan: [] for jan in jans}
        for start in range(0, len(jans), CATALOG_BATCH_SIZE):
            batch = jans[start : start + CATALOG_BATCH_SIZE]
            payload = self._call(
                "catalog",
                client.search_catalog_items,
                identifiers=",".join(batch),
                identifiersType="JAN",
                marketplaceIds=[self.marketplace_id],
                includedData="identifiers,summaries,salesRanks,productTypes",
                pageSize=CATALOG_BATCH_SIZE,
            )
            for raw in payload.get("items", []):
                for product in parse_catalog_item(raw, set(batch), self.marketplace_id):
                    result[product.jan].append(product)
        return result

    def get_offers(self, asin: str) -> AmazonOffers:
        self._require_credentials()
        from sp_api.api import Products

        payload = self._call(
            "offers", Products(**self._kwargs()).get_item_offers, asin, item_condition="New",
            MarketplaceId=self.marketplace_id,
        )
        return parse_offers(payload)

    def estimate_fees(self, asin: str, price: float, is_fba: bool) -> float:
        self._require_credentials()
        from sp_api.api import ProductFees

        payload = self._call(
            "fees", ProductFees(**self._kwargs()).get_product_fees_estimate_for_asin, asin, price,
            currency="JPY", is_fba=is_fba, marketplace_id=self.marketplace_id,
        )
        return parse_fees(payload)

    def get_restrictions(self, asin: str, condition_type: str) -> list[str]:
        self._require_credentials()
        from sp_api.api import ListingsRestrictions

        payload = self._call(
            "restrictions", ListingsRestrictions(**self._kwargs()).get_listings_restrictions,
            asin=asin, sellerId=self.config.seller_id, marketplaceIds=[self.marketplace_id],
            conditionType=condition_type,
        )
        return parse_restrictions(payload)
