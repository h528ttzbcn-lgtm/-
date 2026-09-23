from amazon_arbitrage_finder.models import AmazonOffers, AmazonProduct, SourceItem
from amazon_arbitrage_finder.profit import calculate_profit
from amazon_arbitrage_finder.reporter import build_listing_rows, write_listing_sheet, write_report
from amazon_arbitrage_finder.research_service import prefilter, research
from amazon_arbitrage_finder.settings import ResearchSettings

JAN_A = "4901234567894"
JAN_B = "4912345678904"


def make_item(**overrides):
    defaults = dict(
        source="yahoo", shop_id="joshin", shop_name="Joshin", item_code="1", title="イヤホン",
        url="https://example.com/1", price=10000, shipping_cost=0.0, points=100, jan=JAN_A,
    )
    defaults.update(overrides)
    return SourceItem(**defaults)


def make_settings(**overrides):
    defaults = dict(min_profit=500, min_roi=0.05, inbound_shipping_per_unit=0, check_restrictions=True)
    defaults.update(overrides)
    return ResearchSettings(**defaults)


class FakeAmazon:
    def __init__(self, products=None, offers=None, fees=1500, restrictions=None):
        self.products = products or {}
        self.offers = offers or {}
        self.fees = fees
        self.restrictions = restrictions or {}
        self.calls = []

    def search_by_jans(self, jans):
        self.calls.append(("catalog", tuple(jans)))
        return {jan: self.products.get(jan, []) for jan in jans}

    def get_offers(self, asin):
        self.calls.append(("offers", asin))
        return self.offers[asin]

    def estimate_fees(self, asin, price, is_fba):
        self.calls.append(("fees", asin))
        return self.fees

    def get_restrictions(self, asin, condition_type):
        self.calls.append(("restrictions", asin))
        return self.restrictions.get(asin, [])


def test_profit_counts_points_shipping_and_extras():
    item = make_item(price=10000, shipping_cost=None, points=100, source="rakuten")
    settings = make_settings(unknown_shipping_cost=800, extra_point_rate={"rakuten": 0.05}, inbound_shipping_per_unit=200)
    p = calculate_profit(item, sell_price=15000, amazon_fees=1500, settings=settings)
    # cost = 10000 + 800 - (100 + 500) + 200 = 10400
    assert p.total_cost == 10400
    assert p.profit == 15000 - 1500 - 10400
    assert round(p.roi, 4) == round(3100 / 10400, 4)


def test_prefilter_dedupes_by_jan_and_drops_unmatchable():
    items = [
        make_item(price=12000, shop_id="expensive"),
        make_item(price=9000, shop_id="cheap"),
        make_item(jan=None),
        make_item(jan=JAN_B, title="展示品 イヤホン"),
        make_item(jan=JAN_B, in_stock=False),
    ]
    kept, rejected = prefilter(items, make_settings())
    assert [c.item.shop_id for c in kept] == ["cheap"]
    assert sorted(c.status for c in rejected) == sorted(["重複", "JANなし", "除外キーワード", "在庫なし"])


def test_research_end_to_end():
    products = {
        JAN_A: [AmazonProduct(asin="B0OK000001", jan=JAN_A, product_type="HEADPHONES", sales_rank=100)],
        JAN_B: [AmazonProduct(asin="B0LOW00001", jan=JAN_B)],
    }
    offers = {
        "B0OK000001": AmazonOffers(buybox_price=15000, lowest_price=14500, offer_count=3),
        "B0LOW00001": AmazonOffers(buybox_price=10100, offer_count=2),
    }
    amazon = FakeAmazon(products=products, offers=offers)
    items = [
        make_item(),
        make_item(jan=JAN_B, item_code="2"),
        make_item(jan="0036000291452", item_code="3"),  # not on Amazon
    ]
    results = research(items, amazon, make_settings())
    by_status = {c.status: c for c in results}

    ok = by_status["OK"]
    assert ok.product.asin == "B0OK000001"
    assert ok.profit.profit == 15000 - 1500 - (10000 - 100)
    assert by_status["利益不足"].product.asin == "B0LOW00001"
    assert "Amazonなし" in by_status
    # low-margin item never reached the fee estimate or restriction check
    assert ("fees", "B0LOW00001") not in amazon.calls
    assert ("restrictions", "B0LOW00001") not in amazon.calls
    # catalog lookups are batched into a single call
    assert sum(1 for c in amazon.calls if c[0] == "catalog") == 1


def test_research_filters_rank_restrictions_and_missing_price():
    products = {
        JAN_A: [
            AmazonProduct(asin="B0RANK0001", jan=JAN_A, sales_rank=999999),
            AmazonProduct(asin="B0REST0001", jan=JAN_A, sales_rank=10),
            AmazonProduct(asin="B0NOPR0001", jan=JAN_A, sales_rank=10),
        ]
    }
    offers = {
        "B0REST0001": AmazonOffers(buybox_price=20000, offer_count=1),
        "B0NOPR0001": AmazonOffers(),
    }
    amazon = FakeAmazon(products=products, offers=offers, restrictions={"B0REST0001": ["承認が必要"]})
    results = research([make_item()], amazon, make_settings(max_sales_rank=50000))
    statuses = {c.product.asin: c.status for c in results}
    assert statuses == {"B0RANK0001": "ランキング圏外", "B0REST0001": "出品制限", "B0NOPR0001": "価格なし"}
    assert all("ASINあり" in c.reasons[0] for c in results)


def test_research_records_errors_and_continues():
    class Boom(FakeAmazon):
        def get_offers(self, asin):
            raise RuntimeError("throttled")

    products = {JAN_A: [AmazonProduct(asin="B0ERR00001", jan=JAN_A)]}
    [result] = research([make_item()], Boom(products=products), make_settings())
    assert result.status == "エラー" and "throttled" in result.reasons[0]


def test_reports_and_listing_sheet(tmp_path):
    products = {JAN_A: [AmazonProduct(asin="B0OK000001", jan=JAN_A, product_type="HEADPHONES")]}
    offers = {"B0OK000001": AmazonOffers(buybox_price=15000, offer_count=3)}
    settings = make_settings(sku_prefix="T-", listing_quantity=0)
    results = research([make_item(), make_item(jan=None)], FakeAmazon(products=products, offers=offers), settings)

    rows = build_listing_rows(results, settings)
    assert rows == [
        {
            "sku": "T-B0OK000001", "asin": "B0OK000001", "price": 15000, "quantity": 0,
            "condition_type": "new_new", "product_type": "HEADPHONES", "currency": "JPY",
            "fulfillment_channel": "DEFAULT",
        }
    ]
    report = write_report(results, tmp_path, "t")
    listing = write_listing_sheet(results, settings, tmp_path, "t")
    lines = report.read_text(encoding="utf-8-sig").splitlines()
    assert lines[1].startswith("OK,")  # OK rows first
    assert listing.read_text().splitlines()[0] == "sku,asin,price,quantity,condition_type,product_type,currency,fulfillment_channel"
    assert write_listing_sheet([], settings, tmp_path, "empty") is None
