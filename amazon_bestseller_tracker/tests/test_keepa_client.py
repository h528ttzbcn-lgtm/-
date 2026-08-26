from amazon_bestseller_tracker.keepa_client import KeepaClient


def test_parse_stats_jp_domain_keeps_price_as_is():
    client = KeepaClient(api_key="key", domain="JP")
    product = {
        "stats": {
            "avg30": [None, 1900, None, 120],  # index 1=NEW price, 3=SALES rank
            "current": [None, 1980, None, 100],
        }
    }

    stats = client._parse_stats(product, days=30)

    assert stats == {
        "keepa_avg_price": 1900.0,
        "keepa_avg_rank": 120,
        "keepa_current_price": 1980.0,
        "keepa_current_rank": 100,
    }


def test_parse_stats_converts_minor_currency_units_for_non_jp_domain():
    client = KeepaClient(api_key="key", domain="US")
    product = {
        "stats": {
            "avg30": [None, 1999],  # 1999 cents = $19.99
            "current": [None, 2500],
        }
    }

    stats = client._parse_stats(product, days=30)

    assert stats["keepa_avg_price"] == 19.99
    assert stats["keepa_current_price"] == 25.0


def test_parse_stats_treats_negative_and_missing_values_as_none():
    client = KeepaClient(api_key="key", domain="JP")
    product = {"stats": {"avg30": [None, -1], "current": []}}

    stats = client._parse_stats(product, days=30)

    assert stats["keepa_avg_price"] is None
    assert stats["keepa_avg_rank"] is None
    assert stats["keepa_current_price"] is None
    assert stats["keepa_current_rank"] is None


def test_get_stats_returns_empty_dict_when_keepa_has_no_data(monkeypatch):
    client = KeepaClient(api_key="key", domain="JP")
    fake_api = type("FakeApi", (), {"query": lambda self, *a, **k: []})()
    client._api = fake_api

    assert client.get_stats("B0EXAMPLE1") == {}
