"""Data model for a single product row to run through the profit calculator."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Product:
    product_name: str
    cost_price: float
    selling_price: float
    quantity: int = 1
    category: str = ""
    shipping_cost: float = 0.0
    other_fixed_cost: float = 0.0
    # 消費税の輸出免税還付など、販売に伴い戻ってくる金額(1個あたり)。
    # 適用可否・金額の正当性はご自身の課税事業者区分・輸出通関の証憑等に依存するため、
    # このツールでは判定せず、確認済みの金額をそのまま入力してもらう前提。
    export_tax_refund: float = 0.0
    # この商品individually の目標利益率(0〜1の小数)。未指定ならFeeProfileの
    # default_target_margin_rate を使う。
    target_margin_rate: float | None = None

    def validate(self) -> list[str]:
        errors = []
        if not self.product_name:
            errors.append("product_name is empty")
        if self.cost_price is None or self.cost_price < 0:
            errors.append(f"cost_price must be >= 0, got {self.cost_price}")
        if self.selling_price is None or self.selling_price <= 0:
            errors.append(f"selling_price must be > 0, got {self.selling_price}")
        if self.quantity is None or self.quantity < 0:
            errors.append(f"quantity must be >= 0, got {self.quantity}")
        if self.shipping_cost is None or self.shipping_cost < 0:
            errors.append(f"shipping_cost must be >= 0, got {self.shipping_cost}")
        if self.other_fixed_cost is None or self.other_fixed_cost < 0:
            errors.append(f"other_fixed_cost must be >= 0, got {self.other_fixed_cost}")
        if self.export_tax_refund is None or self.export_tax_refund < 0:
            errors.append(f"export_tax_refund must be >= 0, got {self.export_tax_refund}")
        if self.target_margin_rate is not None and not (0 <= self.target_margin_rate < 1):
            errors.append(f"target_margin_rate must be in [0, 1), got {self.target_margin_rate}")
        return errors
