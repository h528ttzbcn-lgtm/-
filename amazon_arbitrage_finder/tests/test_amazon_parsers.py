import pytest

from amazon_arbitrage_finder.amazon_client import parse_catalog_item, parse_fees, parse_offers, parse_restrictions

MP = "A1VC38T7YXB528"


def test_parse_catalog_item():
    raw = {
        "asin": "B0TEST0001",
        "identifiers": [{"marketplaceId": MP, "identifiers": [{"identifierType": "EAN", "identifier": "4901234567894"}]}],
        "summaries": [{"marketplaceId": MP, "itemName": "イヤホン", "brand": "ACME"}],
        "productTypes": [{"marketplaceId": MP, "productType": "HEADPHONES"}],
        "salesRanks": [{"marketplaceId": MP, "displayGroupRanks": [{"title": "家電&カメラ", "rank": 1234}]}],
    }
    [product] = parse_catalog_item(raw, {"4901234567894"}, MP)
    assert (product.asin, product.jan, product.brand, product.product_type) == (
        "B0TEST0001", "4901234567894", "ACME", "HEADPHONES"
    )
    assert product.sales_rank == 1234


def test_parse_offers():
    payload = {
        "Summary": {
            "TotalOfferCount": 5,
            "BuyBoxPrices": [{"condition": "New", "LandedPrice": {"Amount": 15000}}],
            "LowestPrices": [
                {"condition": "new", "fulfillmentChannel": "Amazon", "LandedPrice": {"Amount": 14800}},
                {"condition": "new", "fulfillmentChannel": "Merchant", "LandedPrice": {"Amount": 14500}},
                {"condition": "used", "fulfillmentChannel": "Merchant", "LandedPrice": {"Amount": 9000}},
            ],
        }
    }
    offers = parse_offers(payload)
    assert (offers.buybox_price, offers.lowest_price, offers.offer_count) == (15000, 14500, 5)
    assert parse_offers({}).buybox_price is None


def test_parse_fees():
    payload = {"FeesEstimateResult": {"Status": "Success", "FeesEstimate": {"TotalFeesEstimate": {"Amount": 1950}}}}
    assert parse_fees(payload) == 1950
    with pytest.raises(RuntimeError, match="見積もり"):
        parse_fees({"FeesEstimateResult": {"Status": "ClientError", "Error": {"Message": "bad asin"}}})


def test_parse_restrictions():
    assert parse_restrictions({"restrictions": []}) == []
    payload = {"restrictions": [{"reasons": [{"message": "ブランドの承認が必要です", "reasonCode": "APPROVAL_REQUIRED"}]}]}
    assert parse_restrictions(payload) == ["ブランドの承認が必要です"]
