import hashlib
import hmac

from unittest.mock import MagicMock

from shopee_stock_watcher.config import ShopeeConfig
from shopee_stock_watcher.shopee_client import ShopeeApiError, ShopeeClient


def make_config(**overrides):
    defaults = dict(
        partner_id=1000,
        partner_key="secret",
        shop_id=2000,
        access_token="token",
        refresh_token="rtoken",
        api_host="https://partner.shopeemobile.com",
        redirect_url="http://localhost:8765/callback",
    )
    defaults.update(overrides)
    return ShopeeConfig(**defaults)


def test_sign_matches_manual_hmac():
    client = ShopeeClient(make_config())
    signature = client._sign("/api/v2/product/unlist_item", 1700000000, extra="tokenshop")

    expected_base = "1000/api/v2/product/unlist_item1700000000tokenshop"
    expected = hmac.new(b"secret", expected_base.encode(), hashlib.sha256).hexdigest()

    assert signature == expected


def test_build_authorization_url_contains_required_params():
    client = ShopeeClient(make_config())
    url = client.build_authorization_url()

    assert "partner_id=1000" in url
    assert "sign=" in url
    assert "redirect=http://localhost:8765/callback" in url


def test_parse_raises_on_error_field():
    response = MagicMock()
    response.json.return_value = {"error": "invalid_access_token", "message": "token expired"}

    try:
        ShopeeClient._parse(response)
        assert False, "expected ShopeeApiError"
    except ShopeeApiError as exc:
        assert "invalid_access_token" in str(exc)
        assert exc.response_body["error"] == "invalid_access_token"


def test_parse_passes_through_success():
    response = MagicMock()
    response.json.return_value = {"response": {"item_list": []}}

    data = ShopeeClient._parse(response)
    assert data == {"response": {"item_list": []}}


def test_unlist_items_empty_list_skips_network_call(monkeypatch):
    client = ShopeeClient(make_config())
    called = {"count": 0}

    def fake_post(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("should not be called for empty item_ids")

    monkeypatch.setattr("shopee_stock_watcher.shopee_client.requests.post", fake_post)

    result = client.unlist_items([], unlist=True)

    assert called["count"] == 0
    assert result == {"response": {"item_list": []}}
