"""
pricing_engine.py — deterministic Pricing Intelligence: all financial
arithmetic happens here in code, never delegated to an LLM. The goal is
"understand the economically viable price range and explain the
trade-offs," not "always match the cheapest competitor."
"""

from __future__ import annotations


def variable_cost(
    price: float, cogs: float, referral_fee_pct: float, fulfillment_fee: float,
    other_cost: float, ad_cost_per_unit: float = 0.0,
) -> float:
    referral_fee = price * referral_fee_pct
    return round(cogs + referral_fee + fulfillment_fee + other_cost + ad_cost_per_unit, 2)


def contribution_margin(
    price: float, cogs: float, referral_fee_pct: float, fulfillment_fee: float,
    other_cost: float, ad_cost_per_unit: float = 0.0,
) -> dict:
    vc = variable_cost(price, cogs, referral_fee_pct, fulfillment_fee, other_cost, ad_cost_per_unit)
    contribution = round(price - vc, 2)
    margin_pct = round(contribution / price, 4) if price > 0 else None
    return {"variable_cost": vc, "contribution": contribution, "margin_pct": margin_pct}


def breakeven_price(cogs: float, referral_fee_pct: float, fulfillment_fee: float, other_cost: float) -> float | None:
    fixed = cogs + fulfillment_fee + other_cost
    denom = 1 - referral_fee_pct
    if denom <= 0:
        return None
    return round(fixed / denom, 2)


def target_margin_price(
    cogs: float, referral_fee_pct: float, fulfillment_fee: float, other_cost: float, target_margin_pct: float,
) -> float | None:
    fixed = cogs + fulfillment_fee + other_cost
    denom = 1 - referral_fee_pct - target_margin_pct
    if denom <= 0:
        return None  # target margin is mathematically unreachable given this fee structure
    return round(fixed / denom, 2)


def price_distribution(observed_prices: list[float], current_price: float) -> dict:
    if not observed_prices:
        return {"lowest": None, "highest": None, "median": None, "average": None,
                "pct_diff_from_median": None, "sample_size": 0}
    sorted_p = sorted(observed_prices)
    n = len(sorted_p)
    median = sorted_p[n // 2] if n % 2 == 1 else (sorted_p[n // 2 - 1] + sorted_p[n // 2]) / 2
    average = sum(sorted_p) / n
    pct_diff = (current_price - median) / median * 100 if median else None
    return {
        "lowest": round(sorted_p[0], 2),
        "highest": round(sorted_p[-1], 2),
        "median": round(median, 2),
        "average": round(average, 2),
        "pct_diff_from_median": round(pct_diff, 1) if pct_diff is not None else None,
        "sample_size": n,
    }


def classify_price_state(margin_pct: float | None, target_margin_pct: float, current_price: float, median_competitor: float | None) -> str:
    if margin_pct is None:
        return "UNKNOWN"
    if margin_pct < target_margin_pct:
        return "BELOW_MARGIN_FLOOR"
    if median_competitor is None or median_competitor <= 0:
        return "HEALTHY_RANGE"
    diff_pct = (current_price - median_competitor) / median_competitor
    if diff_pct > 0.15:
        return "ABOVE_COMPETITIVE_RANGE"
    if diff_pct < -0.10:
        return "COMPETITIVE_PRESSURE"
    return "HEALTHY_RANGE"


def recommend_price_range(
    target_margin_price_value: float | None, median_competitor: float | None, price_state: str,
    price_spread: dict | None = None,
) -> dict:
    """price_spread, when given, is a price_distribution() result --
    used only for contradiction handling (spec §20): a median built from
    wildly disagreeing competitor observations must not be presented
    with the same confidence as one built from agreeing observations."""
    candidates: list[float] = []
    reasoning: list[str] = []
    if target_margin_price_value is not None:
        candidates.append(target_margin_price_value)
        reasoning.append(f"Target margin requires at least ${target_margin_price_value:.2f}.")
    if median_competitor is not None:
        candidates.append(median_competitor)
        reasoning.append(f"Competitor median observed at ${median_competitor:.2f}.")

    if not candidates:
        return {"low": None, "high": None, "reasoning": ["Insufficient data to recommend a price range."], "confidence": "none"}

    low = round(min(candidates), 2)
    high = round(max(candidates) * 1.02, 2)
    if low > high:
        low, high = high, low
    confidence = "high" if len(candidates) >= 2 else "medium"

    if price_spread and price_spread.get("sample_size", 0) >= 2 and price_spread.get("median"):
        lo, hi, med = price_spread["lowest"], price_spread["highest"], price_spread["median"]
        relative_spread = (hi - lo) / med if med else 0
        if relative_spread > 0.15:
            reasoning.append(
                f"Competitor observations disagree ({price_spread['sample_size']} prices from "
                f"${lo:.2f} to ${hi:.2f}) — median used, but confidence is lowered accordingly, "
                "not silently trusted."
            )
            confidence = "low"

    if price_state == "HEALTHY_RANGE":
        reasoning.append("No evidence that an immediate price change is necessary.")
    return {"low": low, "high": high, "reasoning": reasoning, "confidence": confidence}


def simulate_price(
    new_price: float, cogs: float, referral_fee_pct: float, fulfillment_fee: float,
    other_cost: float, ad_spend_levels: list[float] | None = None,
) -> dict:
    """SIMULATION only, never labeled as an actual result. Does not
    predict sales volume — only the deterministic contribution math."""
    base = contribution_margin(new_price, cogs, referral_fee_pct, fulfillment_fee, other_cost)
    scenarios = []
    for ad in (ad_spend_levels or [0.0]):
        cm = contribution_margin(new_price, cogs, referral_fee_pct, fulfillment_fee, other_cost, ad_cost_per_unit=ad)
        scenarios.append({"ad_cost_per_unit": ad, **cm})
    return {"price": new_price, "base": base, "ad_spend_scenarios": scenarios}
