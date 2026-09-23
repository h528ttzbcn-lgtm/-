import pytest

from amazon_arbitrage_finder.csv_loader import SheetValidationError, load_manual_items, load_queries


def test_load_queries(tmp_path):
    path = tmp_path / "q.csv"
    path.write_text("source,keyword,shop,min_price,max_price,pages\nrakuten,,biccamera,1000,,2\nYahoo,ドライヤー,,,,\n")
    queries = load_queries(path)
    assert queries[0].shop == "biccamera" and queries[0].min_price == 1000 and queries[0].pages == 2
    assert queries[1].source == "yahoo" and queries[1].pages == 1


def test_load_queries_collects_errors(tmp_path):
    path = tmp_path / "q.csv"
    path.write_text("source,keyword,shop\nyahoo,,joshin\namazon,x,\n")
    with pytest.raises(SheetValidationError) as exc:
        load_queries(path)
    assert "2行目" in str(exc.value) and "3行目" in str(exc.value)


def test_load_manual_items(tmp_path):
    path = tmp_path / "m.csv"
    path.write_text("jan,price,title,shipping_cost,points\n4901234567894,12800,A,,1280\n")
    [item] = load_manual_items(path)
    assert item.source == "manual" and item.jan == "4901234567894"
    assert item.shipping_cost == 0.0 and item.points == 1280


def test_load_manual_items_rejects_bad_jan(tmp_path):
    path = tmp_path / "m.csv"
    path.write_text("jan,price\n4901234567895,1000\n")
    with pytest.raises(SheetValidationError, match="JAN"):
        load_manual_items(path)
