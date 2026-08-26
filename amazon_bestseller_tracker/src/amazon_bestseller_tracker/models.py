"""Data model for a single row of the watchlist sheet (ASINs to track)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WatchAsin:
    """One ASIN whose ranking/price you want to track over time.

    asin: the Amazon catalog ASIN to look up (10 characters).
    memo: free-text note for your own reference (e.g. product name, why
        you're tracking it). Not sent to any API.
    category_hint: optional note of which category ranking you care about,
        for your own reference. Amazon's Catalog Items API returns whichever
        category ranks it has for the ASIN; this field is not used to filter
        the API response.
    """

    asin: str
    memo: str = ""
    category_hint: str = ""

    def validate(self) -> list[str]:
        errors = []
        if not self.asin or len(self.asin) != 10:
            errors.append(f"asin '{self.asin}' does not look like a valid 10-character ASIN")
        return errors
