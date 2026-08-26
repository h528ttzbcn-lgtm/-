"""Writes the current run's rows to a timestamped CSV: a Keepa-style listing
of current rank/price plus deltas since the last time you ran `snapshot`.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path

from .snapshot_service import BestsellerRow

FIELDNAMES = [f.name for f in fields(BestsellerRow)]


def write_report(rows: list[BestsellerRow], output_dir: str | Path = "output") -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"bestseller_data_{timestamp}.csv"

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    return path
