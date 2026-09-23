from unittest.mock import MagicMock

import pytest

from amazon_arbitrage_finder.config import RakutenConfig, YahooConfig
from amazon_arbitrage_finder.models import SearchQuery
from amazon_arbitrage_finder.sources import rakuten_client, yahoo_client
from amazon_arbitrage_finder.sources.rakuten_client import RakutenApiError, RakutenClient, rakuten_points
from amazon_arbitrage_finder.sources.yahoo_client import YahooClient


def _response(status, body):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.text = str(body)
    return resp


def test_rakuten_points_use_tax_excluded_price():
    # 11000円(税込) -> 税抜10000円 × 1% × 5倍 = 500pt
    assert rakuten_points(11000, 5) == 500


def test_rakuten_parse_item_extracts_jan_shipping_points():
    item = rakuten_client.parse_item(
        {
            "itemName": "ワイヤレスイヤホン 新品",
            "itemCaption": "JAN:4901234567894",
            "itemPrice": 11000,
            "itemUrl": "https://item.rakuten.co.jp/x/1/",
            "shopCode": "biccamera",
            "shopName": "楽天ビック",
            "itemCode": "biccamera:1",
            "pointRate": 2,
            "postageFlag": 1,
            "availability": 1,
        }
    )
    assert item.jan == "4901234567894"
    assert item.shipping_cost is None  # 送料別
    assert item.points == 200
    assert item.shop_id == "biccamera"


def test_rakuten_search_paginates_and_sends_auth(monkeypatch):
    monkeypatch.setattr(rakuten_client.time, "sleep", lambda s: None)
    session = MagicMock()
    session.get.side_effect = [
        _response(200, {"Items": [{"itemName": "a", "itemPrice": 1000}], "pageCount": 2}),
        _response(200, {"Items": [{"Item": {"itemName": "b", "itemPrice": 2000}}], "pageCount": 2}),
    ]
    config = RakutenConfig(application_id="app", access_key="key", referer="https://example.com/")
    items = RakutenClient(config, session=session).search(SearchQuery(source="rakuten", shop="biccamera", pages=5))

    assert [i.title for i in items] == ["a", "b"]
    assert session.get.call_count == 2
    _, kwargs = session.get.call_args
    assert kwargs["params"]["accessKey"] == "key"
    assert kwargs["params"]["shopCode"] == "biccamera"
    assert kwargs["params"]["page"] == 2
    assert kwargs["headers"] == {"Referer": "https://example.com/"}


def test_rakuten_error_and_missing_credentials():
    session = MagicMock()
    session.get.return_value = _response(403, {"error": "forbidden", "error_description": "Referer not allowed"})
    client = RakutenClient(RakutenConfig(application_id="app", access_key="key"), session=session)
    with pytest.raises(RakutenApiError, match="Referer not allowed"):
        client.search(SearchQuery(source="rakuten", keyword="x"))
    with pytest.raises(RakutenApiError, match="認証情報"):
        RakutenClient(RakutenConfig(application_id="", access_key="")).search(SearchQuery(source="rakuten", keyword="x"))


def test_yahoo_parse_and_search(monkeypatch):
    monkeypatch.setattr(yahoo_client.time, "sleep", lambda s: None)
    hit = {
        "name": "ドライヤー",
        "code": "yamada-denki_123",
        "url": "https://store.shopping.yahoo.co.jp/yamada-denki/123.html",
        "price": 19800,
        "janCode": "4901234567894",
        "inStock": True,
        "point": {"amount": 198},
        "seller": {"sellerId": "yamada-denki", "name": "ヤマダデンキ Yahoo!店"},
        "shipping": {"code": 2},
    }
    session = MagicMock()
    session.get.return_value = _response(200, {"totalResultsAvailable": 1, "hits": [hit]})
    items = YahooClient(YahooConfig(client_id="cid"), session=session).search(
        SearchQuery(source="yahoo", keyword="ドライヤー", shop="yamada-denki", pages=3)
    )

    assert len(items) == 1  # stops once all results are fetched
    item = items[0]
    assert (item.jan, item.price, item.points, item.shipping_cost) == ("4901234567894", 19800, 198, 0.0)
    params = session.get.call_args.kwargs["params"]
    assert params["seller_id"] == "yamada-denki"
    assert params["appid"] == "cid"
