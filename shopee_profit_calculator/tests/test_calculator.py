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
