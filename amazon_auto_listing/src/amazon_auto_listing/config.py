"""Loads SP-API credentials and runtime settings from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


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
        """True once the minimum credentials needed to call SP-API are present."""
        return bool(self.lwa_app_id and self.lwa_client_secret and self.refresh_token and self.seller_id)


def load_config(env_file: str | None = None) -> SpApiConfig:
    """Load config from a .env file (if present) plus process environment.

    Missing values are returned as empty strings rather than raising, so the
    CLI can still run in --dry-run mode without real credentials and fail
    with a clear message only when it actually needs to call the API.
    """
    load_dotenv(dotenv_path=env_file, override=False)

    return SpApiConfig(
        lwa_app_id=os.getenv("LWA_APP_ID", ""),
        lwa_client_secret=os.getenv("LWA_CLIENT_SECRET", ""),
        refresh_token=os.getenv("SP_API_REFRESH_TOKEN", ""),
        seller_id=os.getenv("SP_API_SELLER_ID", ""),
        marketplace=os.getenv("SP_API_MARKETPLACE", "JP"),
        aws_access_key=os.getenv("SP_API_AWS_ACCESS_KEY") or None,
        aws_secret_key=os.getenv("SP_API_AWS_SECRET_KEY") or None,
        role_arn=os.getenv("SP_API_ROLE_ARN") or None,
    )
