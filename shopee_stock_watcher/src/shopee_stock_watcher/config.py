"""Loads Shopee Open Platform credentials and runtime settings."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class ShopeeConfig:
    partner_id: int
    partner_key: str
    shop_id: int
    access_token: str
    refresh_token: str
    api_host: str
    redirect_url: str

    def is_complete(self) -> bool:
        return bool(self.partner_id and self.partner_key and self.shop_id and self.access_token)

    def is_app_registered(self) -> bool:
        """True once partner_id/partner_key are set, even before shop authorization."""
        return bool(self.partner_id and self.partner_key)


def load_config(env_file: str | None = None) -> ShopeeConfig:
    load_dotenv(dotenv_path=env_file, override=False)

    def _int(name: str) -> int:
        raw = os.getenv(name, "")
        try:
            return int(raw)
        except ValueError:
            return 0

    return ShopeeConfig(
        partner_id=_int("SHOPEE_PARTNER_ID"),
        partner_key=os.getenv("SHOPEE_PARTNER_KEY", ""),
        shop_id=_int("SHOPEE_SHOP_ID"),
        access_token=os.getenv("SHOPEE_ACCESS_TOKEN", ""),
        refresh_token=os.getenv("SHOPEE_REFRESH_TOKEN", ""),
        api_host=os.getenv("SHOPEE_API_HOST", "https://partner.shopeemobile.com"),
        redirect_url=os.getenv("SHOPEE_REDIRECT_URL", "http://localhost:8765/callback"),
    )
