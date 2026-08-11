"""Writes per-item results to a timestamped CSV report."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ListingResult:
    sku: str
    asin: str
    status: str  # "success" | "error" | "dry-run"
    detail: str = ""


def write_report(results: list[ListingResult], output_dir: str | Path = "output") -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"results_{timestamp}.csv"

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "asin", "status", "detail"])
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    return path
