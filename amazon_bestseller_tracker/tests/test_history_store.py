from amazon_bestseller_tracker.history_store import append_snapshot, latest_by_asin, load_history


def test_load_history_missing_file_returns_empty(tmp_path):
    assert load_history(tmp_path / "nope.jsonl") == []


def test_append_and_load_round_trip(tmp_path):
    path = tmp_path / "history" / "snapshot_log.jsonl"

    append_snapshot({"asin": "B0EXAMPLE1", "current_rank": 100}, path)
    append_snapshot({"asin": "B0EXAMPLE1", "current_rank": 90}, path)
    append_snapshot({"asin": "B0EXAMPLE2", "current_rank": 5000}, path)

    history = load_history(path)

    assert len(history) == 3
    assert history[0]["current_rank"] == 100


def test_latest_by_asin_keeps_last_entry_per_asin(tmp_path):
    path = tmp_path / "snapshot_log.jsonl"
    append_snapshot({"asin": "B0EXAMPLE1", "current_rank": 100}, path)
    append_snapshot({"asin": "B0EXAMPLE1", "current_rank": 90}, path)
    append_snapshot({"asin": "B0EXAMPLE2", "current_rank": 5000}, path)

    latest = latest_by_asin(load_history(path))

    assert latest["B0EXAMPLE1"]["current_rank"] == 90
    assert latest["B0EXAMPLE2"]["current_rank"] == 5000


def test_append_snapshot_handles_non_ascii(tmp_path):
    path = tmp_path / "snapshot_log.jsonl"
    append_snapshot({"asin": "B0EXAMPLE1", "title": "洗濯洗剤 詰め替え用"}, path)

    history = load_history(path)

    assert history[0]["title"] == "洗濯洗剤 詰め替え用"
