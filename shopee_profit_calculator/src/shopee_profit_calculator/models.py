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
        return errors
