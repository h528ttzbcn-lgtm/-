"""Research settings (config/research_settings*.json): cost assumptions, filters and
defaults for the generated listing sheet.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path


@dataclass
class ResearchSettings:
    # --- Amazon販売価格の決め方 ---
    # "buybox": カート価格 / "lowest": 新品最安値(送料込み)。カートが無ければ最安値にフォールバック。
    price_basis: str = "buybox"
    undercut_yen: float = 0.0  # 基準価格から何円下げて売る想定か
    is_fba: bool = True  # 手数料見積もりをFBA前提にするか

    # --- 仕入れ側のポイント・送料 ---
    point_value_rate: float = 1.0  # 1ポイントを何円として計算するか
    # ショップ付与分とは別に、自分に付くポイント(楽天SPU、Yahoo!のキャンペーン等)を
    # 仕入れ価格に対する率で指定。例 {"rakuten": 0.05} = 5%
    extra_point_rate: dict = field(default_factory=dict)
    unknown_shipping_cost: float = 800.0  # 「送料別」で金額不明のときに仮定する送料

    # --- 1個あたりの追加コスト ---
    inbound_shipping_per_unit: float = 0.0  # FBA納品送料など
    packaging_per_unit: float = 0.0
    other_cost_per_unit: float = 0.0

    # --- 絞り込み条件 (0 で無効) ---
    min_profit: float = 500.0
    min_roi: float = 0.10
    max_sales_rank: int = 0
    max_offer_count: int = 0
    exclude_brands: list = field(default_factory=list)
    exclude_title_keywords: list = field(default_factory=lambda: ["中古", "訳あり", "アウトレット", "展示品"])
    check_restrictions: bool = True

    # --- 出品CSV(amazon_auto_listing 用)の初期値 ---
    sku_prefix: str = "ARB-"
    # 仕入れて在庫を確保するまで出品しないよう既定は0。仕入れ後に数量を書き換えてください。
    listing_quantity: int = 0
    condition_type: str = "new_new"
    fulfillment_channel: str = "DEFAULT"

    def extra_point_rate_for(self, source: str) -> float:
        return float(self.extra_point_rate.get(source, 0.0))

    def warnings(self) -> list[str]:
        msgs = []
        if self.price_basis not in ("buybox", "lowest"):
            msgs.append(f"price_basis='{self.price_basis}' は buybox / lowest のいずれかにしてください")
        if self.min_roi > 1:
            msgs.append(f"min_roi={self.min_roi} は100%超です。小数(10%なら0.1)で入力しているか確認してください")
        for source, rate in self.extra_point_rate.items():
            if float(rate) > 0.5:
                msgs.append(f"extra_point_rate[{source}]={rate} は50%超です。小数で入力しているか確認してください")
        if self.inbound_shipping_per_unit == 0 and self.is_fba:
            msgs.append("FBA前提ですが inbound_shipping_per_unit(納品送料)が0です。利益が過大になる可能性があります")
        return msgs


def load_settings(path: str | Path | None) -> ResearchSettings:
    if not path:
        return ResearchSettings()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    known = {f.name for f in fields(ResearchSettings)}
    unknown = [k for k in data if k not in known and not k.startswith("_")]
    if unknown:
        raise ValueError(f"{path}: 未知の設定キーがあります: {unknown}")
    return ResearchSettings(**{k: v for k, v in data.items() if k in known})
