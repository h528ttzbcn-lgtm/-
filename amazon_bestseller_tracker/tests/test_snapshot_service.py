from unittest.mock import MagicMock, patch

from amazon_bestseller_tracker.config import TrackerConfig
from amazon_bestseller_tracker.history_store import load_history
from amazon_bestseller_tracker.models import WatchAsin
from amazon_bestseller_tracker.snapshot_service import run_snapshot


def make_config(**overrides):
    defaults = dict(
        lwa_app_id="app",
        lwa_client_secret="secret",
        refresh_token="token",
        marketplace="JP",
    )
    defaults.update(overrides)
    return TrackerConfig(**defaults)


def make_item(**overrides):
    defaults = dict(asin="B0EXAMPLE1", memo="テスト商品")
    defaults.update(overrides)
    return WatchAsin(**defaults)


@patch("amazon_bestseller_tracker.snapshot_service.SpApiClient")
def test_dry_run_never_calls_sp_api(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    rows = run_snapshot(
        [make_item()], make_config(), history_path=tmp_path / "history.jsonl", dry_run=True
    )

    assert len(rows) == 1
    assert rows[0].status == "dry-run"
    mock_client.get_catalog_snapshot.assert_not_called()
    mock_client.get_current_price.assert_not_called()


@patch("amazon_bestseller_tracker.snapshot_service.SpApiClient")
def test_real_run_fetches_snapshot_and_appends_history(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client.get_catalog_snapshot.return_value = {
        "title": "テスト商品",
        "brand": "テストブランド",
        "category": "ホーム&キッチン",
        "sales_rank": 100,
        "image_url": "https://example.com/img.jpg",
    }
    mock_client.get_current_price.return_value = (1980.0, "JPY")
    mock_client_cls.return_value = mock_client

    history_path = tmp_path / "history.jsonl"
    rows = run_snapshot([make_item()], make_config(), history_path=history_path, dry_run=False)

    assert len(rows) == 1
    row = rows[0]
    assert row.status == "ok"
    assert row.title == "テスト商品"
    assert row.current_rank == 100
    assert row.current_price == 1980.0
    assert row.previous_rank is None  # no prior history yet
    assert row.rank_delta is None

    history = load_history(history_path)
    assert len(history) == 1
    assert history[0]["asin"] == "B0EXAMPLE1"
    assert history[0]["current_rank"] == 100


@patch("amazon_bestseller_tracker.snapshot_service.SpApiClient")
def test_second_run_computes_deltas_against_history(mock_client_cls, tmp_path):
    history_path = tmp_path / "history.jsonl"
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    mock_client.get_catalog_snapshot.return_value = {
        "title": "テスト商品",
        "brand": "",
        "category": "ホーム&キッチン",
        "sales_rank": 100,
        "image_url": None,
    }
    mock_client.get_current_price.return_value = (2000.0, "JPY")
    run_snapshot([make_item()], make_config(), history_path=history_path, dry_run=False)

    mock_client.get_catalog_snapshot.return_value["sales_rank"] = 80
    mock_client.get_current_price.return_value = (1800.0, "JPY")
    rows = run_snapshot([make_item()], make_config(), history_path=history_path, dry_run=False)

    row = rows[0]
    assert row.current_rank == 80
    assert row.previous_rank == 100
    assert row.rank_delta == -20
    assert row.current_price == 1800.0
    assert row.previous_price == 2000.0
    assert row.price_delta == -200.0

    assert len(load_history(history_path)) == 2


@patch("amazon_bestseller_tracker.snapshot_service.SpApiClient")
def test_per_asin_error_is_captured_and_does_not_abort_run(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client.get_catalog_snapshot.side_effect = RuntimeError("boom")
    mock_client_cls.return_value = mock_client

    items = [make_item(asin="B0EXAMPLE1"), make_item(asin="B0EXAMPLE2")]
    rows = run_snapshot(items, make_config(), history_path=tmp_path / "history.jsonl", dry_run=False)

    assert len(rows) == 2
    assert all(r.status == "error" for r in rows)
    assert "boom" in rows[0].detail


@patch("amazon_bestseller_tracker.snapshot_service.SpApiClient")
def test_missing_credentials_aborts_run(mock_client_cls, tmp_path):
    mock_client_cls.return_value = MagicMock()

    incomplete_config = make_config(lwa_app_id="")

    try:
        run_snapshot([make_item()], incomplete_config, history_path=tmp_path / "history.jsonl", dry_run=False)
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert "認証情報" in str(exc)


@patch("amazon_bestseller_tracker.snapshot_service.KeepaClient")
@patch("amazon_bestseller_tracker.snapshot_service.SpApiClient")
def test_keepa_stats_are_merged_when_api_key_configured(mock_sp_cls, mock_keepa_cls, tmp_path):
    mock_client = MagicMock()
    mock_client.get_catalog_snapshot.return_value = {
        "title": "テスト商品",
        "brand": "",
        "category": "",
        "sales_rank": 100,
        "image_url": None,
    }
    mock_client.get_current_price.return_value = (1980.0, "JPY")
    mock_sp_cls.return_value = mock_client

    mock_keepa = MagicMock()
    mock_keepa.get_stats.return_value = {"keepa_avg_price": 1900.0, "keepa_avg_rank": 120}
    mock_keepa_cls.return_value = mock_keepa

    config = make_config(keepa_api_key="kkey")
    rows = run_snapshot([make_item()], config, history_path=tmp_path / "history.jsonl", dry_run=False)

    assert rows[0].keepa_avg_price == 1900.0
    assert rows[0].keepa_avg_rank == 120
    mock_keepa_cls.assert_called_once_with("kkey", "JP")
