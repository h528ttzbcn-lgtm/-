"""Minimal Shopee Open Platform v2 API client: OAuth token exchange/refresh
and product unlist/relist. Only the official, documented Open Platform API
is used here — no scraping.

NOTE: Shopee revises its Open Platform API from time to time. The signing
scheme (HMAC-SHA256 over partner_id+path+timestamp[+access_token+shop_id])
has been stable for a long time, but always cross-check exact endpoint
paths/fields against the current docs before relying on this in production:
https://open.shopee.com/documents
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time

import requests

from .config import ShopeeConfig

logger = logging.getLogger(__name__)

TOKEN_GET_PATH = "/api/v2/auth/token/get"
TOKEN_REFRESH_PATH = "/api/v2/auth/access_token/get"
UNLIST_ITEM_PATH = "/api/v2/product/unlist_item"


class ShopeeApiError(RuntimeError):
    def __init__(self, message: str, response_body: dict | None = None):
        super().__init__(message)
        self.response_body = response_body or {}


class ShopeeClient:
    def __init__(self, config: ShopeeConfig):
        self.config = config

    def _sign(self, path: str, timestamp: int, extra: str = "") -> str:
        base_string = f"{self.config.partner_id}{path}{timestamp}{extra}"
        return hmac.new(
            self.config.partner_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # ---- OAuth: app-level (no shop access token yet) ----------------------

    def build_authorization_url(self) -> str:
        """URL to send the merchant to in a browser to authorize your app
        against their shop. Shopee redirects back to redirect_url with
        `code` and `shop_id` query params, which you pass to exchange_token().
        """
        timestamp = int(time.time())
        path = "/api/v2/shop/auth_partner"
        sign = self._sign(path, timestamp)
        return (
            f"{self.config.api_host}{path}"
            f"?partner_id={self.config.partner_id}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
            f"&redirect={self.config.redirect_url}"
        )

    def exchange_token(self, code: str, shop_id: int) -> dict:
        """Exchange the OAuth `code` (from the redirect callback) for an
        access_token + refresh_token. Returns the raw JSON response.
        """
        timestamp = int(time.time())
        sign = self._sign(TOKEN_GET_PATH, timestamp)
        url = (
            f"{self.config.api_host}{TOKEN_GET_PATH}"
            f"?partner_id={self.config.partner_id}&timestamp={timestamp}&sign={sign}"
        )
        body = {"code": code, "shop_id": shop_id, "partner_id": self.config.partner_id}
        response = requests.post(url, json=body, timeout=15)
        return self._parse(response)

    def refresh_access_token(self) -> dict:
        timestamp = int(time.time())
        sign = self._sign(TOKEN_REFRESH_PATH, timestamp)
        url = (
            f"{self.config.api_host}{TOKEN_REFRESH_PATH}"
            f"?partner_id={self.config.partner_id}&timestamp={timestamp}&sign={sign}"
        )
        body = {
            "refresh_token": self.config.refresh_token,
            "shop_id": self.config.shop_id,
            "partner_id": self.config.partner_id,
        }
        response = requests.post(url, json=body, timeout=15)
        return self._parse(response)

    # ---- Shop-level (requires access_token) --------------------------------

    def _shop_signed_url(self, path: str) -> str:
        timestamp = int(time.time())
        extra = f"{self.config.access_token}{self.config.shop_id}"
        sign = self._sign(path, timestamp, extra)
        return (
            f"{self.config.api_host}{path}"
            f"?partner_id={self.config.partner_id}"
            f"&timestamp={timestamp}"
            f"&access_token={self.config.access_token}"
            f"&shop_id={self.config.shop_id}"
            f"&sign={sign}"
        )

    def unlist_items(self, item_ids: list[int], unlist: bool = True) -> dict:
        """Deactivate (unlist=True) or reactivate (unlist=False) the given
        Shopee item_ids in one batch call.
        """
        if not item_ids:
            return {"response": {"item_list": []}}

        url = self._shop_signed_url(UNLIST_ITEM_PATH)
        body = {"item_list": [{"item_id": item_id, "unlist": unlist} for item_id in item_ids]}
        response = requests.post(url, json=body, timeout=15)
        return self._parse(response)

    @staticmethod
    def _parse(response: requests.Response) -> dict:
        try:
            data = response.json()
        except ValueError:
            raise ShopeeApiError(f"Shopee API returned non-JSON response (status={response.status_code})")

        if data.get("error"):
            raise ShopeeApiError(
                f"Shopee API error: {data.get('error')} - {data.get('message')}", response_body=data
            )
        return data
