import textwrap

import pytest

from amazon_auto_listing.csv_loader import SheetValidationError, load_listing_sheet


def test_load_valid_sheet(tmp_path):
    csv_content = textwrap.dedent(
        """\
        sku,asin,price,quantity
        SKU1,B0EXAMPLE1,1000,3
        SKU2,B0EXAMPLE2,2500,0
        """
    )
    path = tmp_path / "sheet.csv"
    path.write_text(csv_content, encoding="utf-8")

    items = load_listing_sheet(path)

    assert len(items) == 2
    assert items[0].sku == "SKU1"
    assert items[0].price == 1000
    assert items[0].condition_type == "new_new"  # default filled in
    assert items[1].quantity == 0


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "sheet.csv"
    path.write_text("sku,asin,quantity\nSKU1,B0EXAMPLE1,3\n", encoding="utf-8")

    with pytest.raises(SheetValidationError):
        load_listing_sheet(path)


def test_invalid_row_is_collected_not_raised_immediately(tmp_path):
    csv_content = textwrap.dedent(
        """\
        sku,asin,price,quantity
        SKU1,B0EXAMPLE1,1000,3
        SKU2,TOOSHORT,2500,1
        SKU3,B0EXAMPLE3,-5,1
        """
    )
    path = tmp_path / "sheet.csv"
    path.write_text(csv_content, encoding="utf-8")

    with pytest.raises(SheetValidationError) as exc_info:
        load_listing_sheet(path)

    message = str(exc_info.value)
    assert "row 3" in message  # SKU2: bad asin
    assert "row 4" in message  # SKU3: bad price
