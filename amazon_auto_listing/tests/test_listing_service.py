from unittest.mock import MagicMock, patch

from amazon_auto_listing.config import SpApiConfig
from amazon_auto_listing.listing_service import run_listings
from amazon_auto_listing.models import ListingItem
from amazon_auto_listing.sp_client import CredentialsMissingError


def make_config(**overrides):
    defaults = dict(
        lwa_app_id="app",
        lwa_client_secret="secret",
        refresh_token="token",
        seller_id="A1SELLER",
        marketplace="JP",
    )
    defaults.update(overrides)
    return SpApiConfig(**defaults)


def make_item(**overrides):
    defaults = dict(sku="SKU1", asin="B0EXAMPLE1", price=1000, quantity=5)
    defaults.update(overrides)
    return ListingItem(**defaults)


@patch("amazon_auto_listing.listing_service.SpApiClient")
def test_dry_run_never_calls_put_listing(mock_client_cls):
    mock_client = MagicMock()
    mock_client.marketplace_id = "A1VC38T7YXB528"
    mock_client_cls.return_value = mock_client

    results = run_listings([make_item()], make_config(), dry_run=True, throttle_seconds=0)

    assert len(results) == 1
    assert results[0].status == "dry-run"
    mock_client.put_listing.assert_not_called()


@patch("amazon_auto_listing.listing_service.SpApiClient")
def test_real_run_reports_success_and_error(mock_client_cls):
    mock_client = MagicMock()
    mock_client.marketplace_id = "A1VC38T7YXB528"
    mock_client.put_listing.side_effect = [
        {"status": "ACCEPTED", "issues": []},
        RuntimeError("boom"),
    ]
    mock_client_cls.return_value = mock_client

    items = [make_item(sku="SKU1"), make_item(sku="SKU2")]
    results = run_listings(items, make_config(), dry_run=False, throttle_seconds=0)

    assert results[0].status == "ACCEPTED"
    assert results[1].status == "error"
    assert "boom" in results[1].detail


@patch("amazon_auto_listing.listing_service.SpApiClient")
def test_missing_credentials_aborts_run(mock_client_cls):
    mock_client = MagicMock()
    mock_client.marketplace_id = "A1VC38T7YXB528"
    mock_client.put_listing.side_effect = CredentialsMissingError("no creds")
    mock_client_cls.return_value = mock_client

    try:
        run_listings([make_item()], make_config(), dry_run=False, throttle_seconds=0)
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert "no creds" in str(exc)
