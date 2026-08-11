from unittest.mock import MagicMock, patch

from shopee_stock_watcher.config import ShopeeConfig
from shopee_stock_watcher.models import WatchItem
from shopee_stock_watcher.state_store import load_state
from shopee_stock_watcher.watcher_service import run_watch


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


def make_item(item_id, status, **overrides):
    defaults = dict(shopee_item_id=item_id, product_name=f"item{item_id}", current_status=status)
    defaults.update(overrides)
    return WatchItem(**defaults)


def test_dry_run_never_calls_shopee_client(tmp_path):
    state_path = tmp_path / "state.json"
    items = [make_item(1, "out_of_stock")]

    with patch("shopee_stock_watcher.watcher_service.ShopeeClient") as mock_cls:
        results = run_watch(items, make_config(), state_path=str(state_path), dry_run=True)

    mock_cls.assert_not_called()
    assert results[0].action == "dry-run-delist"
    # dry-run still records observed status so future comparisons are correct
    assert load_state(state_path) == {1: "out_of_stock"}


def test_real_run_delists_newly_out_of_stock_items(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text('{"1": "in_stock", "2": "in_stock"}', encoding="utf-8")

    items = [make_item(1, "out_of_stock"), make_item(2, "in_stock")]

    mock_client = MagicMock()
    mock_client.unlist_items.return_value = {"response": {}}

    with patch("shopee_stock_watcher.watcher_service.ShopeeClient", return_value=mock_client):
        results = run_watch(items, make_config(), state_path=str(state_path), dry_run=False)

    mock_client.unlist_items.assert_called_once_with([1], unlist=True)
    delisted = [r for r in results if r.action == "delist"]
    assert len(delisted) == 1
    assert delisted[0].shopee_item_id == 1
    assert load_state(state_path) == {1: "out_of_stock", 2: "in_stock"}


def test_auto_relist_calls_unlist_false(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text('{"1": "out_of_stock"}', encoding="utf-8")

    items = [make_item(1, "in_stock")]

    mock_client = MagicMock()
    mock_client.unlist_items.return_value = {"response": {}}

    with patch("shopee_stock_watcher.watcher_service.ShopeeClient", return_value=mock_client):
        results = run_watch(items, make_config(), state_path=str(state_path), dry_run=False, auto_relist=True)

    mock_client.unlist_items.assert_called_once_with([1], unlist=False)
    assert results[0].action == "relist"


def test_missing_credentials_aborts_before_state_save(tmp_path):
    state_path = tmp_path / "state.json"
    items = [make_item(1, "out_of_stock")]
    incomplete_config = make_config(access_token="")

    with patch("shopee_stock_watcher.watcher_service.ShopeeClient"):
        try:
            run_watch(items, incomplete_config, state_path=str(state_path), dry_run=False)
            assert False, "expected SystemExit"
        except SystemExit:
            pass

    assert not state_path.exists()
