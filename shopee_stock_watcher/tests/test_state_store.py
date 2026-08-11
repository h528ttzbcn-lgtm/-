from shopee_stock_watcher.state_store import load_state, save_state


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_state({111: "in_stock", 222: "out_of_stock"}, path)

    loaded = load_state(path)

    assert loaded == {111: "in_stock", 222: "out_of_stock"}
    assert all(isinstance(k, int) for k in loaded)


def test_load_missing_file_returns_empty_dict(tmp_path):
    path = tmp_path / "does_not_exist.json"
    assert load_state(path) == {}
