import textwrap

import pytest

from shopee_stock_watcher.csv_loader import SheetValidationError, load_watchlist


def test_load_valid_sheet(tmp_path):
    csv_content = textwrap.dedent(
        """\
        shopee_item_id,product_name,current_status
        111,商品A,in_stock
        222,商品B,out_of_stock
        """
    )
    path = tmp_path / "sheet.csv"
    path.write_text(csv_content, encoding="utf-8")

    items = load_watchlist(path)

    assert len(items) == 2
    assert items[0].shopee_item_id == 111
    assert items[1].current_status == "out_of_stock"
    assert items[0].source_price is None  # optional column defaulted


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "sheet.csv"
    path.write_text("shopee_item_id,product_name\n111,商品A\n", encoding="utf-8")

    with pytest.raises(SheetValidationError):
        load_watchlist(path)


def test_invalid_status_is_collected_not_raised_immediately(tmp_path):
    csv_content = textwrap.dedent(
        """\
        shopee_item_id,product_name,current_status
        111,商品A,in_stock
        222,商品B,maybe
        333,商品C,out_of_stock
        """
    )
    path = tmp_path / "sheet.csv"
    path.write_text(csv_content, encoding="utf-8")

    with pytest.raises(SheetValidationError) as exc_info:
        load_watchlist(path)

    assert "row 3" in str(exc_info.value)
