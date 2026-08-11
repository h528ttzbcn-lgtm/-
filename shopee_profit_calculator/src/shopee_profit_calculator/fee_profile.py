"""Loads and validates a Shopee fee profile (config/fee_profile*.json).

All rates default to 0 so a missing/unfilled profile fails loudly (via
`warnings()`) instead of silently producing an over-optimistic profit
number. Fee rates are country/category/program-specific and change over
time on Shopee's side, so this module never hardcodes real-world figures —
the user must fill them in from their own Seller Centre.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FeeProfile:
    marketplace: str = ""
    currency: str = ""
    commission_rate_default: float = 0.0
    commission_rate_by_category: dict = field(default_factory=dict)
    transaction_fee_rate: float = 0.0
    service_fee_rate: float = 0.0
    fixed_fee_per_order: float = 0.0

    def commission_rate_for(self, category: str) -> float:
        if category and category in self.commission_rate_by_category:
            return float(self.commission_rate_by_category[category])
        return float(self.commission_rate_default)

    def total_rate_for(self, category: str) -> float:
        """Sum of all percentage-based fees (as a fraction of selling price)."""
        return self.commission_rate_for(category) + self.transaction_fee_rate + self.service_fee_rate

    def warnings(self) -> list[str]:
        """Non-fatal sanity warnings — a profile with everything at 0 almost
        certainly hasn't been filled in yet, and unrealistic rates (>50%)
        usually indicate a units mistake (e.g. entering "5" instead of "0.05").
        """
        msgs = []
        if not self.marketplace:
            msgs.append("marketplace が未設定です")
        if not self.currency:
            msgs.append("currency が未設定です")
        if (
            self.commission_rate_default == 0.0
            and not self.commission_rate_by_category
            and self.transaction_fee_rate == 0.0
            and self.service_fee_rate == 0.0
            and self.fixed_fee_per_order == 0.0
        ):
            msgs.append(
                "手数料が全て0のままです。Shopeeセラーセンターの実際の手数料を確認して "
                "fee_profile.json に反映してください(未設定だと利益が過大に出ます)"
            )
        for rate_name, rate_value in [
            ("commission_rate_default", self.commission_rate_default),
            ("transaction_fee_rate", self.transaction_fee_rate),
            ("service_fee_rate", self.service_fee_rate),
        ]:
            if rate_value > 0.5:
                msgs.append(
                    f"{rate_name}={rate_value} は50%を超えています。"
                    f"小数(例: 5%なら0.05)で入力しているか確認してください"
                )
        return msgs


def load_fee_profile(path: str | Path) -> FeeProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.pop("_readme", None)
    data.pop("_example_category_name", None)
    if "commission_rate_by_category" in data:
        data["commission_rate_by_category"] = {
            k: v for k, v in data["commission_rate_by_category"].items() if not k.startswith("_")
        }
    return FeeProfile(**data)
