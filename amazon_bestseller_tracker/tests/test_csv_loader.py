from pathlib import Path

import pytest

from amazon_bestseller_tracker.csv_loader import SheetValidationError, load_watchlist


def write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "watchlist.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_watchlist_fills_optional_defaults(tmp_path):
    path = write_csv(tmp_path, "asin\nB0EXAMPLE1\nB0EXAMPLE2\n")

    items = load_watchlist(path)

    assert len(items) == 2
    assert items[0].asin == "B0EXAMPLE1"
    assert items[0].memo == ""
    assert items[0].category_hint == ""


def test_load_watchlist_reads_optional_columns(tmp_path):
    path = write_csv(tmp_path, "asin,memo,category_hint\nB0EXAMPLE1,競合A,家電\n")

    items = load_watchlist(path)

    assert items[0].memo == "競合A"
    assert items[0].category_hint == "家電"


def test_load_watchlist_missing_required_column_raises(tmp_path):
    path = write_csv(tmp_path, "memo\nfoo\n")

    with pytest.raises(SheetValidationError, match="asin"):
        load_watchlist(path)


def test_load_watchlist_invalid_asin_raises(tmp_path):
    path = write_csv(tmp_path, "asin\nTOOSHORT\n")

    with pytest.raises(SheetValidationError, match="TOOSHORT"):
        load_watchlist(path)
