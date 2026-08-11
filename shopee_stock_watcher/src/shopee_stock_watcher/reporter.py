"""Writes per-item action results to a timestamped CSV report."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ActionResult:
    shopee_item_id: int
    product_name: str
    source_asin: str
    previous_status: str
    current_status: str
    action: str  # "delist" | "relist" | "none" | "dry-run-delist" | "dry-run-relist"
    result: str  # "ok" | "error" | "skipped"
    detail: str = ""


def write_report(results: list[ActionResult], output_dir: str | Path = "output") -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"stock_watch_{timestamp}.csv"

    fieldnames = [
        "shopee_item_id",
        "product_name",
        "source_asin",
        "previous_status",
        "current_status",
        "action",
        "result",
        "detail",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    return path
