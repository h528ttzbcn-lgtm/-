"""Compares the current watchlist against last-known state and decides which
items need a Shopee listing action.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import WatchItem


@dataclass
class Transition:
    item: WatchItem
    previous_status: str | None  # None if never seen before
    action: str  # "delist" | "relist" | "none"


def compute_transitions(items: list[WatchItem], previous_state: dict[int, str], auto_relist: bool) -> list[Transition]:
    transitions = []
    for item in items:
        previous_status = previous_state.get(item.shopee_item_id)

        action = "none"
        if item.current_status == "out_of_stock" and previous_status != "out_of_stock":
            # Newly out of stock (including first time we've ever seen it) -> delist.
            action = "delist"
        elif auto_relist and item.current_status == "in_stock" and previous_status == "out_of_stock":
            # Was delisted for being out of stock, now back in stock -> relist.
            action = "relist"

        transitions.append(Transition(item=item, previous_status=previous_status, action=action))

    return transitions


def next_state(items: list[WatchItem], previous_state: dict[int, str]) -> dict[int, str]:
    new_state = dict(previous_state)
    for item in items:
        new_state[item.shopee_item_id] = item.current_status
    return new_state
