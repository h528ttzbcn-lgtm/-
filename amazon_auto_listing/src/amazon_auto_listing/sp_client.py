"""Thin wrapper around python-amazon-sp-api for the calls this tool needs."""
from __future__ import annotations

import logging

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import SpApiConfig

logger = logging.getLogger(__name__)


class CredentialsMissingError(RuntimeError):
    pass


def _marketplace(config: SpApiConfig):
    from sp_api.base import Marketplaces

    try:
        return getattr(Marketplaces, config.marketplace)
    except AttributeError as exc:
        valid = [m.name for m in Marketplaces]
        raise ValueError(
            f"未知のマーケットプレイス '{config.marketplace}'。有効な値: {valid}"
        ) from exc


class SpApiClient:
    """Lazily imports python-amazon-sp-api so --dry-run works without it installed
    against real credentials, and raises a clear error if credentials are missing
    at the moment an actual API call is attempted.
    """

    def __init__(self, config: SpApiConfig):
        self.config = config

    def _require_credentials(self):
        if not self.config.is_complete():
            raise CredentialsMissingError(
                "SP-API 認証情報が不足しています。.env を設定してください "
                "(LWA_APP_ID, LWA_CLIENT_SECRET, SP_API_REFRESH_TOKEN, SP_API_SELLER_ID)。"
                " README.md の「SP-API 認証情報の取得手順」を参照してください。"
            )

    @property
    def marketplace_id(self) -> str:
        return _marketplace(self.config).marketplace_id

    def put_listing(self, sku: str, body: dict) -> dict:
        """Create/update a listing offer for `sku` via PUT /listings/items."""
        self._require_credentials()
        return self._put_listing_with_retry(sku, body)

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(Exception),
    )
    def _put_listing_with_retry(self, sku: str, body: dict) -> dict:
        from sp_api.api import ListingsItems
        from sp_api.base import SellingApiException

        client = ListingsItems(marketplace=_marketplace(self.config), credentials=self.config.credentials_dict())
        try:
            response = client.put_listings_item(
                sellerId=self.config.seller_id,
                sku=sku,
                marketplaceIds=[self.marketplace_id],
                body=body,
            )
            return response.payload
        except SellingApiException as exc:
            # Let tenacity retry on transient errors (e.g. 429/5xx); it will
            # eventually re-raise the last exception if all attempts fail.
            logger.warning("SP-API error while listing sku=%s: %s", sku, exc)
            raise

    def get_catalog_item_product_types(self, asin: str) -> list[str]:
        """Look up the candidate product types for an ASIN, to help fill in
        the `product_type` column of the input sheet.
        """
        self._require_credentials()
        from sp_api.api import CatalogItems

        client = CatalogItems(marketplace=_marketplace(self.config), credentials=self.config.credentials_dict())
        response = client.get_catalog_item(asin, marketplaceIds=[self.marketplace_id], includedData=["productTypes"])
        product_types = response.payload.get("productTypes", [])
        return [pt.get("productType") for pt in product_types if pt.get("productType")]

    def get_product_type_schema(self, product_type: str) -> dict:
        """Fetch the required-attributes schema for a product type, so a custom
        templates/<PRODUCT_TYPE>.json can be authored correctly.
        """
        self._require_credentials()
        from sp_api.api import ProductTypeDefinitions

        client = ProductTypeDefinitions(
            marketplace=_marketplace(self.config), credentials=self.config.credentials_dict()
        )
        response = client.get_definitions_product_type(
            product_type, marketplaceIds=[self.marketplace_id], requirements="LISTING"
        )
        return response.payload
