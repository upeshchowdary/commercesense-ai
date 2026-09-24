import pytest

from pricing_engine import (
    breakeven_price,
    classify_price_state,
    contribution_margin,
    price_distribution,
    recommend_price_range,
    simulate_price,
    target_margin_price,
)


def test_contribution_margin_basic():
    result = contribution_margin(price=19.99, cogs=5.81, referral_fee_pct=0.15, fulfillment_fee=3.09, other_cost=0.45)
    # variable_cost = 5.81 + 19.99*0.15 + 3.09 + 0.45 = 5.81+2.9985+3.09+0.45 = 12.3485 -> 12.35 (rounded)
    assert result["variable_cost"] == pytest.approx(12.35, abs=0.01)
    assert result["contribution"] == pytest.approx(19.99 - 12.35, abs=0.02)
    assert result["margin_pct"] < 0.42  # below the 42% target used in this exact scenario


def test_breakeven_and_target_margin_price_ordering():
    be = breakeven_price(cogs=5.81, referral_fee_pct=0.15, fulfillment_fee=3.09, other_cost=0.45)
    tmp = target_margin_price(cogs=5.81, referral_fee_pct=0.15, fulfillment_fee=3.09, other_cost=0.45, target_margin_pct=0.30)
    assert be is not None and tmp is not None
    assert tmp > be  # reaching a positive target margin always requires a higher price than merely breaking even


def test_target_margin_price_unreachable_returns_none():
    # referral fee alone exceeds 100% minus target -> mathematically impossible
    assert target_margin_price(cogs=5, referral_fee_pct=0.9, fulfillment_fee=1, other_cost=0, target_margin_pct=0.5) is None


def test_price_distribution_empty_is_honest():
    result = price_distribution([], current_price=20)
    assert result["sample_size"] == 0
    assert result["median"] is None


def test_price_distribution_basic():
    result = price_distribution([18, 19, 20, 21, 22], current_price=25)
    assert result["median"] == 20
    assert result["pct_diff_from_median"] == pytest.approx(25.0, abs=0.1)


def test_classify_price_state_below_margin_floor():
    assert classify_price_state(margin_pct=0.20, target_margin_pct=0.35, current_price=20, median_competitor=19) == "BELOW_MARGIN_FLOOR"


def test_classify_price_state_above_competitive_range():
    assert classify_price_state(margin_pct=0.40, target_margin_pct=0.30, current_price=30, median_competitor=20) == "ABOVE_COMPETITIVE_RANGE"


def test_classify_price_state_unknown_without_margin():
    assert classify_price_state(margin_pct=None, target_margin_pct=0.30, current_price=20, median_competitor=20) == "UNKNOWN"


def test_recommend_price_range_never_a_single_magic_number():
    result = recommend_price_range(target_margin_price_value=14.20, median_competitor=14.69, price_state="BELOW_MARGIN_FLOOR")
    assert result["low"] is not None and result["high"] is not None
    assert result["low"] <= result["high"]
    assert len(result["reasoning"]) >= 2


def test_recommend_price_range_insufficient_data():
    result = recommend_price_range(None, None, "UNKNOWN")
    assert result["low"] is None
    assert result["confidence"] == "none"


def test_recommend_price_range_downgrades_confidence_on_contradictory_observations():
    # Spec §20/§50: $14.99, $18.99, $15.29 disagree by >15% of the median
    # -- more than any single-source noise should produce. The engine
    # must not silently trust the median at "high" confidence here.
    spread = price_distribution([14.99, 18.99, 15.29], current_price=15.00)
    result = recommend_price_range(
        target_margin_price_value=14.20, median_competitor=spread["median"],
        price_state="HEALTHY_RANGE", price_spread=spread,
    )
    assert result["confidence"] == "low"
    assert any("disagree" in r for r in result["reasoning"])


def test_recommend_price_range_stays_high_confidence_when_observations_agree():
    spread = price_distribution([14.99, 15.05, 15.10], current_price=15.00)
    result = recommend_price_range(
        target_margin_price_value=14.20, median_competitor=spread["median"],
        price_state="HEALTHY_RANGE", price_spread=spread,
    )
    assert result["confidence"] == "high"
    assert not any("disagree" in r for r in result["reasoning"])


def test_simulate_price_is_pure_math_not_volume_prediction():
    result = simulate_price(new_price=17.99, cogs=5.81, referral_fee_pct=0.15, fulfillment_fee=3.09, other_cost=0.45,
                             ad_spend_levels=[0, 2, 4])
    assert result["price"] == 17.99
    assert len(result["ad_spend_scenarios"]) == 3
    # higher ad spend must strictly reduce contribution, all else equal
    contributions = [s["contribution"] for s in result["ad_spend_scenarios"]]
    assert contributions == sorted(contributions, reverse=True)
