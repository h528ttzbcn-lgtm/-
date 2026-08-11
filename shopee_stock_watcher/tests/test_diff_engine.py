from shopee_stock_watcher.diff_engine import compute_transitions, next_state
from shopee_stock_watcher.models import WatchItem


def make_item(item_id=1, status="in_stock", **overrides):
    defaults = dict(shopee_item_id=item_id, product_name=f"item{item_id}", current_status=status)
    defaults.update(overrides)
    return WatchItem(**defaults)


def test_first_time_seen_out_of_stock_delists():
    items = [make_item(1, "out_of_stock")]
    transitions = compute_transitions(items, previous_state={}, auto_relist=False)
    assert transitions[0].action == "delist"
    assert transitions[0].previous_status is None


def test_already_out_of_stock_does_nothing_again():
    items = [make_item(1, "out_of_stock")]
    transitions = compute_transitions(items, previous_state={1: "out_of_stock"}, auto_relist=False)
    assert transitions[0].action == "none"


def test_in_stock_to_out_of_stock_delists():
    items = [make_item(1, "out_of_stock")]
    transitions = compute_transitions(items, previous_state={1: "in_stock"}, auto_relist=False)
    assert transitions[0].action == "delist"


def test_relist_disabled_by_default():
    items = [make_item(1, "in_stock")]
    transitions = compute_transitions(items, previous_state={1: "out_of_stock"}, auto_relist=False)
    assert transitions[0].action == "none"


def test_relist_when_enabled():
    items = [make_item(1, "in_stock")]
    transitions = compute_transitions(items, previous_state={1: "out_of_stock"}, auto_relist=True)
    assert transitions[0].action == "relist"


def test_in_stock_staying_in_stock_does_nothing():
    items = [make_item(1, "in_stock")]
    transitions = compute_transitions(items, previous_state={1: "in_stock"}, auto_relist=True)
    assert transitions[0].action == "none"


def test_next_state_merges_and_overwrites():
    items = [make_item(1, "out_of_stock"), make_item(2, "in_stock")]
    state = next_state(items, previous_state={1: "in_stock", 3: "in_stock"})
    assert state == {1: "out_of_stock", 2: "in_stock", 3: "in_stock"}
