"""Research pipeline: source items -> JAN dedupe -> Amazon match -> price/fees -> filters.

Checks are ordered cheapest first so the slow SP-API calls (getItemOffers is
limited to 0.5 req/s) are only spent on items that can still pass:
local filters -> catalog lookup (batched) -> rank/brand -> offers ->
rough profit without fees -> fee estimate -> ROI/profit -> restrictions.
"""
from __future__ import annotations

import logging
from typing import Protocol

from .models import AmazonOffers, AmazonProduct, Candidate, SourceItem
from .profit import calculate_profit, purchase_cost, target_sell_price
from .settings import ResearchSettings

logger = logging.getLogger(__name__)


class AmazonLookup(Protocol):
    def search_by_jans(self, jans: list[str]) -> dict[str, list[AmazonProduct]]: ...
    def get_offers(self, asin: str) -> AmazonOffers: ...
    def estimate_fees(self, asin: str, price: float, is_fba: bool) -> float: ...
    def get_restrictions(self, asin: str, condition_type: str) -> list[str]: ...


def prefilter(items: list[SourceItem], settings: ResearchSettings) -> tuple[list[Candidate], list[Candidate]]:
    """Local-only checks. Returns (kept, rejected); kept has one cheapest item per JAN."""
    rejected: list[Candidate] = []
    best: dict[str, Candidate] = {}
    excluded_words = [w.lower() for w in settings.exclude_title_keywords]

    for item in items:
        cand = Candidate(item=item)
        if not item.in_stock:
            rejected.append(cand.reject("在庫なし"))
            continue
        if not item.jan:
            rejected.append(cand.reject("JANなし", "JANコードが取得できずAmazonと照合できません"))
            continue
        hit = next((w for w in excluded_words if w in item.title.lower()), None)
        if hit:
            rejected.append(cand.reject("除外キーワード", f"商品名に「{hit}」を含む"))
            continue

        current = best.get(item.jan)
        if current is None:
            best[item.jan] = cand
            continue
        # Same JAN from several shops: only research the cheapest effective cost.
        if purchase_cost(item, settings)[2] < purchase_cost(current.item, settings)[2]:
            best[item.jan], cand = cand, current
        rejected.append(cand.reject("重複", f"同じJAN({item.jan})でより安い仕入れ先あり"))

    return list(best.values()), rejected


def _evaluate(cand: Candidate, amazon: AmazonLookup, settings: ResearchSettings) -> Candidate:
    product = cand.product
    if settings.max_sales_rank and (product.sales_rank is None or product.sales_rank > settings.max_sales_rank):
        return cand.reject("ランキング圏外", f"ランキング {product.sales_rank} > {settings.max_sales_rank}")
    excluded_brands = {b.lower() for b in settings.exclude_brands}
    if product.brand and product.brand.lower() in excluded_brands:
        return cand.reject("除外ブランド", product.brand)

    cand.offers = amazon.get_offers(product.asin)
    if settings.max_offer_count and cand.offers.offer_count > settings.max_offer_count:
        return cand.reject("出品者過多", f"出品者数 {cand.offers.offer_count} > {settings.max_offer_count}")
    sell_price = target_sell_price(cand.offers, settings)
    if sell_price is None:
        return cand.reject("価格なし", "Amazonに新品の出品が無く販売価格の基準がありません")

    _, _, total_cost = purchase_cost(cand.item, settings)
    if sell_price - total_cost < settings.min_profit:
        # Fees only lower profit further, so skip the fee-estimate call.
        cand.profit = calculate_profit(cand.item, sell_price, 0.0, settings)
        return cand.reject("利益不足", "手数料を引く前の時点で最低利益に届きません")

    fees = amazon.estimate_fees(product.asin, sell_price, settings.is_fba)
    cand.profit = calculate_profit(cand.item, sell_price, fees, settings)
    if cand.profit.profit < settings.min_profit:
        return cand.reject("利益不足", f"利益 {cand.profit.profit:.0f}円 < {settings.min_profit:.0f}円")
    if settings.min_roi and (cand.profit.roi is None or cand.profit.roi < settings.min_roi):
        return cand.reject("ROI不足", f"ROI {(cand.profit.roi or 0) * 100:.1f}% < {settings.min_roi * 100:.1f}%")

    if settings.check_restrictions:
        restrictions = amazon.get_restrictions(product.asin, settings.condition_type)
        if restrictions:
            return cand.reject("出品制限", " / ".join(restrictions))

    cand.status = "OK"
    return cand


def research(items: list[SourceItem], amazon: AmazonLookup, settings: ResearchSettings) -> list[Candidate]:
    kept, results = prefilter(items, settings)
    logger.info("照合対象 %d件 (除外 %d件)。AmazonカタログをJANで検索します…", len(kept), len(results))

    matches = amazon.search_by_jans([c.item.jan for c in kept])
    for cand in kept:
        products = matches.get(cand.item.jan) or []
        if not products:
            results.append(cand.reject("Amazonなし", "このJANの商品がAmazonカタログにありません"))
            continue
        for product in products:
            # A JAN mapping to several ASINs (e.g. bundle listings) is evaluated per ASIN.
            evaluated = Candidate(item=cand.item, product=product)
            if len(products) > 1:
                evaluated.reasons.append(f"同一JANに{len(products)}件のASINあり。数量・セット内容を要確認")
            try:
                results.append(_evaluate(evaluated, amazon, settings))
            except Exception as exc:  # keep going; one bad ASIN shouldn't stop the run
                logger.warning("ASIN %s の調査に失敗: %s", product.asin, exc)
                results.append(evaluated.reject("エラー", str(exc)))

    ok = sum(1 for r in results if r.is_ok)
    logger.info("利益候補 %d件 / 全 %d件", ok, len(results))
    return results
