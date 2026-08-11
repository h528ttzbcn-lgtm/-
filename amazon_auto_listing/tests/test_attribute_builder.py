from amazon_auto_listing.attribute_builder import build_attributes, build_listing_body
from amazon_auto_listing.models import ListingItem


def make_item(**overrides):
    defaults = dict(
        sku="MY-SKU-1",
        asin="B0EXAMPLE1",
        price=1980,
        quantity=10,
        condition_type="new_new",
        product_type="PRODUCT",
        currency="JPY",
        fulfillment_channel="DEFAULT",
    )
    defaults.update(overrides)
    return ListingItem(**defaults)


def test_build_attributes_substitutes_all_fields():
    item = make_item()
    attrs = build_attributes(item, marketplace_id="A1VC38T7YXB528")

    assert attrs["merchant_suggested_asin"][0]["value"] == "B0EXAMPLE1"
    assert attrs["merchant_suggested_asin"][0]["marketplace_id"] == "A1VC38T7YXB528"
    assert attrs["condition_type"][0]["value"] == "new_new"
    offer = attrs["purchasable_offer"][0]
    assert offer["currency"] == "JPY"
    assert offer["our_price"][0]["schedule"][0]["value_with_tax"] == 1980
    assert attrs["fulfillment_availability"][0]["quantity"] == 10
    assert "_comment" not in attrs


def test_build_listing_body_includes_product_type():
    item = make_item(product_type="LUGGAGE")
    body = build_listing_body(item, marketplace_id="A1VC38T7YXB528")

    assert body["productType"] == "LUGGAGE"
    assert body["requirements"] == "LISTING"
    assert "attributes" in body


def test_unknown_product_type_falls_back_to_generic_template():
    item = make_item(product_type="SOME_UNUSED_TYPE")
    attrs = build_attributes(item, marketplace_id="A1VC38T7YXB528")

    # falls back to generic.json without raising
    assert attrs["merchant_suggested_asin"][0]["value"] == item.asin
