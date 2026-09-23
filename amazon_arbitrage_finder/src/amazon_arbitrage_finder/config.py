"""Loads API credentials (Rakuten / Yahoo! / Amazon SP-API) from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_RAKUTEN_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
DEFAULT_YAHOO_ENDPOINT = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"


@dataclass(frozen=True)
class RakutenConfig:
    application_id: str
    access_key: str
    referer: str = ""
    endpoint: str = DEFAULT_RAKUTEN_ENDPOINT

    def is_complete(self) -> bool:
        return bool(self.application_id and self.access_key)


@dataclass(frozen=True)
class YahooConfig:
    client_id: str
    endpoint: str = DEFAULT_YAHOO_ENDPOINT

    def is_complete(self) -> bool:
        return bool(self.client_id)


@dataclass(frozen=True)
class SpApiConfig:
    lwa_app_id: str
    lwa_client_secret: str
    refresh_token: str
    seller_id: str
    marketplace: str
    aws_access_key: str | None = None
    aws_secret_key: str | None = None
    role_arn: str | None = None

    def credentials_dict(self) -> dict:
        """Shape expected by python-amazon-sp-api's `credentials=` kwarg."""
        creds = {
            "refresh_token": self.refresh_token,
            "lwa_app_id": self.lwa_app_id,
            "lwa_client_secret": self.lwa_client_secret,
        }
        if self.aws_access_key:
            creds["aws_access_key"] = self.aws_access_key
        if self.aws_secret_key:
            creds["aws_secret_key"] = self.aws_secret_key
        if self.role_arn:
            creds["role_arn"] = self.role_arn
        return creds

    def is_complete(self) -> bool:
        return bool(self.lwa_app_id and self.lwa_client_secret and self.refresh_token and self.seller_id)


@dataclass(frozen=True)
class AppConfig:
    rakuten: RakutenConfig
    yahoo: YahooConfig
    sp_api: SpApiConfig


def load_config(env_file: str | None = None) -> AppConfig:
    """Load all credentials from a .env file (if present) plus process environment.

    Missing values are returned as empty strings rather than raising, so each
    client can fail with a clear message only when it is actually used.
    """
    load_dotenv(dotenv_path=env_file, override=False)

    return AppConfig(
        rakuten=RakutenConfig(
            application_id=os.getenv("RAKUTEN_APPLICATION_ID", ""),
            access_key=os.getenv("RAKUTEN_ACCESS_KEY", ""),
            referer=os.getenv("RAKUTEN_REFERER", ""),
            endpoint=os.getenv("RAKUTEN_ENDPOINT") or DEFAULT_RAKUTEN_ENDPOINT,
        ),
        yahoo=YahooConfig(
            client_id=os.getenv("YAHOO_CLIENT_ID", ""),
            endpoint=os.getenv("YAHOO_ENDPOINT") or DEFAULT_YAHOO_ENDPOINT,
        ),
        sp_api=SpApiConfig(
            lwa_app_id=os.getenv("LWA_APP_ID", ""),
            lwa_client_secret=os.getenv("LWA_CLIENT_SECRET", ""),
            refresh_token=os.getenv("SP_API_REFRESH_TOKEN", ""),
            seller_id=os.getenv("SP_API_SELLER_ID", ""),
            marketplace=os.getenv("SP_API_MARKETPLACE", "JP"),
            aws_access_key=os.getenv("SP_API_AWS_ACCESS_KEY") or None,
            aws_secret_key=os.getenv("SP_API_AWS_SECRET_KEY") or None,
            role_arn=os.getenv("SP_API_ROLE_ARN") or None,
        ),
    )
