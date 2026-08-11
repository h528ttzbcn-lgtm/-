import textwrap

import pytest

from shopee_profit_calculator.csv_loader import SheetValidationError, load_product_sheet


def test_load_valid_sheet(tmp_path):
    csv_content = textwrap.dedent(
        """\
        product_name,cost_price,selling_price
        商品A,450,1280
        商品B,780,2480
        """
    )
    path = tmp_path / "sheet.csv"
    path.write_text(csv_content, encoding="utf-8")

    products = load_product_sheet(path)

    assert len(products) == 2
    assert products[0].product_name == "商品A"
    assert products[0].quantity == 1  # default filled in
    assert products[1].cost_price == 780


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "sheet.csv"
    path.write_text("product_name,cost_price\n商品A,450\n", encoding="utf-8")

    with pytest.raises(SheetValidationError):
        load_product_sheet(path)


def test_invalid_row_is_collected_not_raised_immediately(tmp_path):
    csv_content = textwrap.dedent(
        """\
        product_name,cost_price,selling_price
        商品A,450,1280
        商品B,-100,2480
        商品C,300,-5
        """
    )
    path = tmp_path / "sheet.csv"
    path.write_text(csv_content, encoding="utf-8")

    with pytest.raises(SheetValidationError) as exc_info:
        load_product_sheet(path)

    message = str(exc_info.value)
    assert "row 3" in message  # negative cost_price
    assert "row 4" in message  # negative selling_price
