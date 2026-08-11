"""Persists the last-known status per Shopee item_id between runs, so the
diff engine can tell "in_stock -> out_of_stock" transitions apart from
"already known to be out_of_stock".
"""
from __future__ import annotations

import json
from pathlib import Path


def load_state(path: str | Path) -> dict[int, str]:
    path = Path(path)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw.items()}


def save_state(state: dict[int, str], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({str(k): v for k, v in state.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
