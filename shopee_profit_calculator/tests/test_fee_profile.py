import json

from shopee_profit_calculator.fee_profile import load_fee_profile


def test_load_fee_profile_strips_comment_keys(tmp_path):
    data = {
        "_readme": "ignore me",
        "marketplace": "TW",
        "currency": "TWD",
        "commission_rate_default": 0.05,
        "commission_rate_by_category": {"_example_category_name": 0.0, "electronics": 0.06},
        "transaction_fee_rate": 0.02,
        "service_fee_rate": 0.0,
        "fixed_fee_per_order": 0.0,
    }
    path = tmp_path / "fee_profile.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    profile = load_fee_profile(path)

    assert profile.marketplace == "TW"
    assert "_example_category_name" not in profile.commission_rate_by_category
    assert profile.commission_rate_by_category["electronics"] == 0.06


def test_all_zero_profile_warns():
    from shopee_profit_calculator.fee_profile import FeeProfile

    profile = FeeProfile()
    warnings = profile.warnings()
    assert any("全て0" in w for w in warnings)


def test_unrealistic_rate_warns():
    from shopee_profit_calculator.fee_profile import FeeProfile

    profile = FeeProfile(marketplace="TW", currency="TWD", commission_rate_default=5.0)
    warnings = profile.warnings()
    assert any("50%を超えています" in w for w in warnings)


def test_reasonable_profile_has_no_warnings():
    from shopee_profit_calculator.fee_profile import FeeProfile

    profile = FeeProfile(marketplace="TW", currency="TWD", commission_rate_default=0.05, transaction_fee_rate=0.02)
    assert profile.warnings() == []
