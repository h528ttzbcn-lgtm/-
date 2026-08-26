"""Appends each snapshot run to a JSONL log, so repeated runs build up your
own Keepa-style price/sales-rank history for tracked ASINs. There is no
official Amazon API that returns historical rank/price data, so this is
entirely self-accumulated from your own periodic `snapshot` runs.
"""
from __future__ import annotations

import json
from pathlib import Path


def append_snapshot(entry: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    entries = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def latest_by_asin(history: list[dict]) -> dict[str, dict]:
    """Most recent entry per ASIN, assuming `history` is in chronological
    (append) order — later entries for the same ASIN overwrite earlier ones.
    """
    latest: dict[str, dict] = {}
    for entry in history:
        asin = entry.get("asin")
        if asin:
            latest[asin] = entry
    return latest
