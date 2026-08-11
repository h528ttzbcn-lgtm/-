from shopee_profit_calculator.calculator import calculate_profit
from shopee_profit_calculator.fee_profile import FeeProfile
from shopee_profit_calculator.models import Product


def test_profitable_product():
    product = Product(product_name="A", cost_price=450, selling_price=1280, quantity=20, category="electronics")
    fees = FeeProfile(
        marketplace="TEST",
        currency="TEST",
        commission_rate_default=0.05,
        commission_rate_by_category={"electronics": 0.06},
        transaction_fee_rate=0.02,
    )

    result = calculate_profit(product, fees)

    # commission uses category override (0.06), not default (0.05)
    assert result.commission_fee == 1280 * 0.06
    assert result.transaction_fee == 1280 * 0.02
    expected_profit = 1280 - 450 - (1280 * 0.06) - (1280 * 0.02)
    assert round(result.profit_per_unit, 6) == round(expected_profit, 6)
    assert abs(result.profit_total - result.profit_per_unit * 20) < 1e-9
    assert result.is_profitable is True
    assert result.margin_rate == result.profit_per_unit / 1280


def test_unprofitable_product_flagged():
    product = Product(product_name="B", cost_price=1000, selling_price=1050, shipping_cost=100)
    fees = FeeProfile(commission_rate_default=0.1, transaction_fee_rate=0.05)

    result = calculate_profit(product, fees)

    assert result.is_profitable is False
    assert result.profit_per_unit < 0


def test_break_even_price_is_consistent():
    product = Product(product_name="C", cost_price=500, selling_price=1000, shipping_cost=50)
    fees = FeeProfile(commission_rate_default=0.08, transaction_fee_rate=0.02)

    result = calculate_profit(product, fees)

    # Re-run the calculation at exactly the break-even price: profit should be ~0
    at_break_even = Product(
        product_name="C",
        cost_price=product.cost_price,
        selling_price=result.break_even_price,
        shipping_cost=product.shipping_cost,
    )
    re_result = calculate_profit(at_break_even, fees)
    assert abs(re_result.profit_per_unit) < 1e-6


def test_zero_selling_price_does_not_raise_divide_by_zero():
    # calculate_profit is deliberately permissive (validation happens separately
    # in Product.validate / csv_loader) so this must not raise ZeroDivisionError.
    product = Product(product_name="D", cost_price=100, selling_price=0.0, quantity=1)
    fees = FeeProfile()
    result = calculate_profit(product, fees)
    assert result.margin_rate is None


def test_export_tax_refund_increases_profit():
    base = Product(product_name="E", cost_price=500, selling_price=1000)
    with_refund = Product(product_name="E", cost_price=500, selling_price=1000, export_tax_refund=50)
    fees = FeeProfile(commission_rate_default=0.05)

    base_result = calculate_profit(base, fees)
    refund_result = calculate_profit(with_refund, fees)

    assert round(refund_result.profit_per_unit - base_result.profit_per_unit, 6) == 50


def test_recommended_price_hits_target_margin_when_reapplied():
    product = Product(product_name="F", cost_price=500, selling_price=900, target_margin_rate=0.2)
    fees = FeeProfile(commission_rate_default=0.05, transaction_fee_rate=0.02)

    result = calculate_profit(product, fees)
    assert result.recommended_price is not None

    at_recommended = Product(
        product_name="F", cost_price=500, selling_price=result.recommended_price, target_margin_rate=0.2
    )
    re_result = calculate_profit(at_recommended, fees)
    assert abs(re_result.margin_rate - 0.2) < 1e-6


def test_price_action_up_when_recommended_above_tolerance():
    # Selling price far below what's needed for a 30% margin -> 値上げ推奨
    product = Product(product_name="G", cost_price=500, selling_price=600, target_margin_rate=0.3)
    fees = FeeProfile(commission_rate_default=0.05)

    result = calculate_profit(product, fees)
    assert result.price_action == "値上げ推奨"
    assert result.price_diff > 0


def test_price_action_down_when_recommended_below_tolerance():
    # Selling price far above what's needed for a 5% margin -> 値下げ推奨
    product = Product(product_name="H", cost_price=500, selling_price=2000, target_margin_rate=0.05)
    fees = FeeProfile(commission_rate_default=0.05)

    result = calculate_profit(product, fees)
    assert result.price_action == "値下げ推奨"
    assert result.price_diff < 0


def test_price_action_hold_within_tolerance():
    product = Product(product_name="I", cost_price=500, selling_price=900, target_margin_rate=0.2)
    fees = FeeProfile(commission_rate_default=0.05, transaction_fee_rate=0.02)

    # First find the exact recommended price, then re-run at that price:
    # diff should be ~0, well within the default tolerance -> "維持"
    first = calculate_profit(product, fees)
    at_recommended = Product(
        product_name="I", cost_price=500, selling_price=first.recommended_price, target_margin_rate=0.2
    )
    result = calculate_profit(at_recommended, fees)
    assert result.price_action == "維持"


def test_no_target_margin_skips_recommendation():
    product = Product(product_name="J", cost_price=500, selling_price=1000)
    fees = FeeProfile(commission_rate_default=0.05)  # default_target_margin_rate defaults to 0

    result = calculate_profit(product, fees)
    assert result.target_margin_rate is None
    assert result.recommended_price is None
    assert result.price_action == "目標未設定"


def test_row_target_margin_overrides_fee_profile_default():
    product = Product(product_name="K", cost_price=500, selling_price=1000, target_margin_rate=0.1)
    fees = FeeProfile(commission_rate_default=0.05, default_target_margin_rate=0.5)

    result = calculate_profit(product, fees)
    assert result.target_margin_rate == 0.1


def test_unreachable_target_margin_is_flagged():
    # commission (0.05) + target margin (0.98) >= 1 -> impossible to price for
    product = Product(product_name="L", cost_price=500, selling_price=1000, target_margin_rate=0.98)
    fees = FeeProfile(commission_rate_default=0.05)

    result = calculate_profit(product, fees)
    assert result.recommended_price is None
    assert "達成不可" in result.price_action
