import csv

from amazon_bestseller_tracker.reporter import write_report
from amazon_bestseller_tracker.snapshot_service import BestsellerRow


def test_write_report_creates_csv_with_expected_columns(tmp_path):
    rows = [
        BestsellerRow(
            asin="B0EXAMPLE1",
            memo="テスト商品",
            title="テスト商品名",
            current_rank=100,
            previous_rank=120,
            rank_delta=-20,
            current_price=1980.0,
            currency="JPY",
            status="ok",
        )
    ]

    path = write_report(rows, output_dir=tmp_path)

    assert path.exists()
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        written = list(reader)

    assert len(written) == 1
    assert written[0]["asin"] == "B0EXAMPLE1"
    assert written[0]["current_rank"] == "100"
    assert written[0]["rank_delta"] == "-20"
    assert written[0]["status"] == "ok"


def test_write_report_creates_output_dir(tmp_path):
    output_dir = tmp_path / "nested" / "output"

    path = write_report([], output_dir=output_dir)

    assert output_dir.exists()
    assert path.exists()
