"""Tests for the pure payload-parsing helpers in sp_client.py -- these don't
touch the network or import the sp_api SDK, so they run without credentials
or the python-amazon-sp-api package's runtime dependencies.
"""
from amazon_bestseller_tracker.sp_client import extract_catalog_snapshot, extract_price


def test_extract_catalog_snapshot_full_payload():
    payload = {
        "summaries": [{"itemName": "テスト商品", "brand": "テストブランド"}],
        "salesRanks": [
            {
                "displayGroupRanks": [{"title": "ホーム&キッチン", "rank": 42}],
            }
        ],
        "images": [{"images": [{"link": "https://example.com/img.jpg"}]}],
    }

    snapshot = extract_catalog_snapshot(payload)

    assert snapshot == {
        "title": "テスト商品",
        "brand": "テストブランド",
        "category": "ホーム&キッチン",
        "sales_rank": 42,
        "image_url": "https://example.com/img.jpg",
    }


def test_extract_catalog_snapshot_falls_back_to_classification_ranks():
    payload = {
        "summaries": [{"itemName": "テスト商品"}],
        "salesRanks": [{"classificationRanks": [{"title": "文房具", "rank": 7}]}],
        "images": [],
    }

    snapshot = extract_catalog_snapshot(payload)

    assert snapshot["category"] == "文房具"
    assert snapshot["sales_rank"] == 7
    assert snapshot["image_url"] is None


def test_extract_catalog_snapshot_handles_missing_fields():
    assert extract_catalog_snapshot({}) == {
        "title": "",
        "brand": "",
        "category": "",
        "sales_rank": None,
        "image_url": None,
    }


def test_extract_price_returns_landed_price():
    payload = [
        {
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "Price": {
                                "LandedPrice": {"CurrencyCode": "JPY", "Amount": 1980.0},
                            }
                        }
                    ]
                }
            }
        }
    ]

    price, currency = extract_price(payload)

    assert price == 1980.0
    assert currency == "JPY"


def test_extract_price_handles_empty_payload():
    assert extract_price([]) == (None, "")
    assert extract_price(None) == (None, "")


def test_extract_price_handles_missing_competitive_prices():
    payload = [{"Product": {"CompetitivePricing": {"CompetitivePrices": []}}}]

    assert extract_price(payload) == (None, "")
