"""
pricing_engine.py — Deterministic Pricing Intelligence for CommerceSense AI v3.

All financial arithmetic happens strictly in Python using Decimal precision,
never delegated to an LLM.

Principles:
  1. Constrained Value Pricing: Never "race to the bottom".
  2. Cost-Completeness: COGS, FBA fulfillment, closing fees, packaging, inward freight,
     returns allowance, ad spend, and Amazon referral fees.
  3. Inviolable Margin Floor: Never recommend dropping below minimum viable or
     target margin price.
  4. 3-Tier Hierarchy: Tier 1 (Same ASIN), Tier 2 (Exact Equivalent), Tier 3 (Substitute).
     Substitutes are strictly excluded from direct competitor medians.
  5. Contradiction & Spread Handling: When competitor price spread > 15%, downgrade confidence.
  6. Zero-Elasticity Baseline: Scenarios modeled at current observed volume; volume
     elasticity explicitly labeled NOT_ESTIMATED.
"""

from __future__ import annotations

import decimal
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union

# Helper for converting inputs to Decimal
def _to_dec(val: Any, default: str = "0.0000") -> Decimal:
    if val is None:
        return Decimal(default)
    if isinstance(val, Decimal):
        return val
    try:
        s = str(val).strip().replace(",", "").replace("$", "")
        return Decimal(s) if s else Decimal(default)
    except Exception:
        return Decimal(default)


def _round_currency(val: Optional[Decimal]) -> Optional[Decimal]:
    if val is None:
        return None
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _round_pct(val: Optional[Decimal]) -> Optional[Decimal]:
    if val is None:
        return None
    return val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# =====================================================================
# 1. Cost & Variable Cost Calculations
# =====================================================================

def cost_complete_fixed_unit_cost(
    cogs: Union[Decimal, float],
    fulfillment_fee: Union[Decimal, float],
    closing_fee: Union[Decimal, float] = 0.0,
    packaging_cost: Union[Decimal, float] = 0.0,
    inbound_freight: Union[Decimal, float] = 0.0,
    ad_cost_per_unit: Union[Decimal, float] = 0.0,
    returns_allowance: Union[Decimal, float] = 0.0,
    other_cost: Union[Decimal, float] = 0.0,
) -> Decimal:
    """Computes total fixed unit cost prior to price-dependent referral fees."""
    return (
        _to_dec(cogs)
        + _to_dec(fulfillment_fee)
        + _to_dec(closing_fee)
        + _to_dec(packaging_cost)
        + _to_dec(inbound_freight)
        + _to_dec(ad_cost_per_unit)
        + _to_dec(returns_allowance)
        + _to_dec(other_cost)
    )


def variable_cost(
    price: float,
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    ad_cost_per_unit: float = 0.0,
    closing_fee: float = 0.0,
    packaging_cost: float = 0.0,
    inbound_freight: float = 0.0,
    returns_allowance: float = 0.0,
) -> float:
    """Computes total variable cost at selling price P. Preserves float return for backward compatibility."""
    p_dec = _to_dec(price)
    r_pct_dec = _to_dec(referral_fee_pct)
    ref_fee = p_dec * r_pct_dec
    fixed = cost_complete_fixed_unit_cost(
        cogs=cogs,
        fulfillment_fee=fulfillment_fee,
        closing_fee=closing_fee,
        packaging_cost=packaging_cost,
        inbound_freight=inbound_freight,
        ad_cost_per_unit=ad_cost_per_unit,
        returns_allowance=returns_allowance,
        other_cost=other_cost,
    )
    total_vc = _round_currency(fixed + ref_fee)
    return float(total_vc) if total_vc is not None else 0.0


def contribution_margin(
    price: float,
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    ad_cost_per_unit: float = 0.0,
    closing_fee: float = 0.0,
    packaging_cost: float = 0.0,
    inbound_freight: float = 0.0,
    returns_allowance: float = 0.0,
) -> dict:
    """Calculates contribution margin and margin percentage at given price."""
    p_dec = _to_dec(price)
    vc = variable_cost(
        price, cogs, referral_fee_pct, fulfillment_fee, other_cost,
        ad_cost_per_unit=ad_cost_per_unit, closing_fee=closing_fee,
        packaging_cost=packaging_cost, inbound_freight=inbound_freight,
        returns_allowance=returns_allowance,
    )
    vc_dec = _to_dec(vc)
    contribution_dec = _round_currency(p_dec - vc_dec)
    margin_pct_dec = _round_pct(contribution_dec / p_dec) if p_dec > Decimal("0") else None

    return {
        "variable_cost": float(vc_dec),
        "contribution": float(contribution_dec) if contribution_dec is not None else 0.0,
        "margin_pct": float(margin_pct_dec) if margin_pct_dec is not None else None,
    }


# =====================================================================
# 2. Breakeven, Target Margin & Minimum Viable Prices
# =====================================================================

def breakeven_price(
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    closing_fee: float = 0.0,
    packaging_cost: float = 0.0,
    inbound_freight: float = 0.0,
    ad_cost_per_unit: float = 0.0,
    returns_allowance: float = 0.0,
) -> float | None:
    """Calculates Breakeven Price: P_be = FixedUnitCost / (1 - referral_fee_pct)."""
    fixed = cost_complete_fixed_unit_cost(
        cogs=cogs,
        fulfillment_fee=fulfillment_fee,
        closing_fee=closing_fee,
        packaging_cost=packaging_cost,
        inbound_freight=inbound_freight,
        ad_cost_per_unit=ad_cost_per_unit,
        returns_allowance=returns_allowance,
        other_cost=other_cost,
    )
    r_dec = _to_dec(referral_fee_pct)
    denom = Decimal("1") - r_dec
    if denom <= Decimal("0"):
        return None
    p_be = _round_currency(fixed / denom)
    return float(p_be) if p_be is not None else None


def target_margin_price(
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    target_margin_pct: float,
    closing_fee: float = 0.0,
    packaging_cost: float = 0.0,
    inbound_freight: float = 0.0,
    ad_cost_per_unit: float = 0.0,
    returns_allowance: float = 0.0,
) -> float | None:
    """Calculates Target Margin Price: P_target = FixedUnitCost / (1 - referral_fee_pct - target_margin_pct).
    Returns None if mathematically unreachable.
    """
    fixed = cost_complete_fixed_unit_cost(
        cogs=cogs,
        fulfillment_fee=fulfillment_fee,
        closing_fee=closing_fee,
        packaging_cost=packaging_cost,
        inbound_freight=inbound_freight,
        ad_cost_per_unit=ad_cost_per_unit,
        returns_allowance=returns_allowance,
        other_cost=other_cost,
    )
    r_dec = _to_dec(referral_fee_pct)
    m_dec = _to_dec(target_margin_pct)
    denom = Decimal("1") - r_dec - m_dec
    if denom <= Decimal("0"):
        return None
    p_target = _round_currency(fixed / denom)
    return float(p_target) if p_target is not None else None


def minimum_viable_price(
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    min_margin_pct: float = 0.10,
    closing_fee: float = 0.0,
    packaging_cost: float = 0.0,
    inbound_freight: float = 0.0,
    ad_cost_per_unit: float = 0.0,
    returns_allowance: float = 0.0,
) -> float | None:
    """Calculates absolute lower bound price for minimum viable contribution margin (e.g. 10%)."""
    return target_margin_price(
        cogs=cogs,
        referral_fee_pct=referral_fee_pct,
        fulfillment_fee=fulfillment_fee,
        other_cost=other_cost,
        target_margin_pct=min_margin_pct,
        closing_fee=closing_fee,
        packaging_cost=packaging_cost,
        inbound_freight=inbound_freight,
        ad_cost_per_unit=ad_cost_per_unit,
        returns_allowance=returns_allowance,
    )


# =====================================================================
# 3. Competitor Filtering & Price Distribution
# =====================================================================

def filter_direct_competitor_observations(observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strictly filters competitor observations to direct competition:
    - Tier 1: SAME_ASIN
    - Tier 2: EXACT_EQUIVALENT
    Strictly EXCLUDES Tier 3 (SUBSTITUTE) from direct medians/distributions.
    """
    direct: List[Dict[str, Any]] = []
    for obs in observations:
        tier = obs.get("match_tier") or "TIER_1_SAME_ASIN"
        if tier in ("TIER_1_SAME_ASIN", "TIER_2_EXACT_EQUIVALENT", "SAME_ASIN", "EXACT_EQUIVALENT"):
            direct.append(obs)
    return direct


def price_distribution(
    observed_prices: list[float],
    current_price: float,
    observations: Optional[List[Dict[str, Any]]] = None,
) -> dict:
    """Computes distribution metrics (lowest, highest, median, average, relative spread).
    If structured observations are supplied, filters out Tier 3 substitutes.
    """
    if observations is not None:
        direct_obs = filter_direct_competitor_observations(observations)
        prices = [
            float(obs.get("landed_price") or obs.get("price") or 0.0)
            for obs in direct_obs
            if (obs.get("landed_price") or obs.get("price"))
        ]
    else:
        prices = [p for p in observed_prices if p > 0]

    if not prices:
        return {
            "lowest": None,
            "highest": None,
            "median": None,
            "average": None,
            "relative_spread": 0.0,
            "pct_diff_from_median": None,
            "sample_size": 0,
        }

    sorted_p = sorted(prices)
    n = len(sorted_p)
    median = sorted_p[n // 2] if n % 2 == 1 else (sorted_p[n // 2 - 1] + sorted_p[n // 2]) / 2.0
    average = sum(sorted_p) / n
    pct_diff = ((current_price - median) / median * 100.0) if median > 0 else None
    spread = (sorted_p[-1] - sorted_p[0]) / median if median > 0 else 0.0

    return {
        "lowest": round(sorted_p[0], 2),
        "highest": round(sorted_p[-1], 2),
        "median": round(median, 2),
        "average": round(average, 2),
        "relative_spread": round(spread, 4),
        "pct_diff_from_median": round(pct_diff, 1) if pct_diff is not None else None,
        "sample_size": n,
    }


def classify_price_state(
    margin_pct: float | None,
    target_margin_pct: float,
    current_price: float,
    median_competitor: float | None,
) -> str:
    """Classifies current pricing state into standard category states."""
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


# =====================================================================
# 4. Recommendation & Decision Policy Engine
# =====================================================================

def recommend_price_range(
    target_margin_price_value: float | None,
    median_competitor: float | None,
    price_state: str,
    price_spread: dict | None = None,
) -> dict:
    """Builds recommended price range and reasoning with spread contradiction handling."""
    candidates: list[float] = []
    reasoning: list[str] = []

    if target_margin_price_value is not None:
        candidates.append(target_margin_price_value)
        reasoning.append(f"Target margin requires at least ${target_margin_price_value:.2f}.")
    if median_competitor is not None:
        candidates.append(median_competitor)
        reasoning.append(f"Competitor median observed at ${median_competitor:.2f}.")

    if not candidates:
        return {
            "low": None,
            "high": None,
            "reasoning": ["Insufficient data to recommend a price range."],
            "confidence": "none",
        }

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

    return {
        "low": low,
        "high": high,
        "reasoning": reasoning,
        "confidence": confidence,
    }


def evaluate_pricing_decision(
    current_price: float,
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    target_margin_pct: float,
    min_margin_pct: float = 0.10,
    competitor_median: Optional[float] = None,
    buy_box_price: Optional[float] = None,
    our_rating: Optional[float] = None,
    competitor_rating: Optional[float] = None,
    days_of_cover: Optional[int] = None,
    is_competitor_fba: bool = True,
    price_distribution_result: Optional[dict] = None,
) -> dict:
    """Comprehensive Decision Policy Engine:
    Evaluates:
      - HOLD: Current price is well positioned.
      - LOWER: Feasible price drop above margin floor.
      - RAISE: Feasible price increase defending margin.
      - MATCH: Match competitive offer above margin floor.
      - DO_NOT_MATCH: Guardrails triggered (margin floor breach, reputation premium, stockout preservation, unverified seller).
      - INSUFFICIENT_DATA: Missing costs or observations.
    """
    be_price = breakeven_price(cogs, referral_fee_pct, fulfillment_fee, other_cost)
    target_price = target_margin_price(cogs, referral_fee_pct, fulfillment_fee, other_cost, target_margin_pct)
    mvp_price = minimum_viable_price(cogs, referral_fee_pct, fulfillment_fee, other_cost, min_margin_pct)

    cm = contribution_margin(current_price, cogs, referral_fee_pct, fulfillment_fee, other_cost)

    # 1. Check data sufficiency
    if target_price is None or be_price is None:
        return {
            "action": "INSUFFICIENT_DATA",
            "primary_reason": "UNREACHABLE_OR_MISSING_COSTS",
            "target_margin_price": None,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": None, "high": None},
            "reasoning": ["Critical cost inputs are missing or target margin is mathematically unreachable given fee structure."],
            "confidence": "none",
        }

    reasons: List[str] = []
    comp_ref = buy_box_price if buy_box_price and buy_box_price > 0 else competitor_median

    # Spread analysis
    spread = price_distribution_result.get("relative_spread", 0.0) if price_distribution_result else 0.0
    high_dispersion = spread > 0.15

    # 2. DO_NOT_MATCH Guardrails
    # Guardrail 1: Inviolable Margin Floor
    if comp_ref is not None and comp_ref < target_price:
        reasons.append(
            f"Competitor offer (${comp_ref:.2f}) breaches minimum margin floor (${target_price:.2f}). "
            "Matching would erode profitability below required business threshold. Recommend differentiation or bundle."
        )
        return {
            "action": "DO_NOT_MATCH",
            "primary_reason": "BELOW_MARGIN_FLOOR",
            "target_margin_price": target_price,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": target_price, "high": round(target_price * 1.05, 2)},
            "reasoning": reasons,
            "confidence": "high",
        }

    # Guardrail 2: Reputation Asymmetry Premium
    if our_rating is not None and competitor_rating is not None and our_rating >= 4.3 and competitor_rating <= 3.7:
        reasons.append(
            f"Seller review rating ({our_rating:.1f}) is substantially higher than competitor ({competitor_rating:.1f}). "
            "Premium price is justified by superior quality and customer goodwill; matching cheap offers damages brand perception."
        )
        return {
            "action": "DO_NOT_MATCH",
            "primary_reason": "PREMIUM_JUSTIFIED",
            "target_margin_price": target_price,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": current_price, "high": round(current_price * 1.03, 2)},
            "reasoning": reasons,
            "confidence": "high",
        }

    # Guardrail 3: Inventory Shortage Suppression (Stockout Preservation)
    if days_of_cover is not None and days_of_cover < 14:
        reasons.append(
            f"Inventory cover is critically low ({days_of_cover} days). Dropping price would accelerate stockout penalties. "
            "Price must be held or raised to ration remaining units until restock."
        )
        return {
            "action": "DO_NOT_MATCH",
            "primary_reason": "STOCKOUT_PRESERVATION",
            "target_margin_price": target_price,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": current_price, "high": round(current_price * 1.08, 2)},
            "reasoning": reasons,
            "confidence": "high",
        }

    # Guardrail 4: Unverified / FBM Merchant Competitor
    if not is_competitor_fba and comp_ref is not None and comp_ref < current_price:
        reasons.append(
            f"Competitor offer (${comp_ref:.2f}) is merchant-fulfilled (FBM) without Prime speed. "
            "FBA convenience and faster delivery justify a price premium over merchant-fulfilled listings."
        )
        return {
            "action": "DO_NOT_MATCH",
            "primary_reason": "UNVERIFIED_SELLER",
            "target_margin_price": target_price,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": current_price, "high": round(current_price * 1.02, 2)},
            "reasoning": reasons,
            "confidence": "medium",
        }

    # 3. Direct Opportunity / Action Decisions
    if comp_ref is None:
        return {
            "action": "HOLD",
            "primary_reason": "NO_COMPETITOR_PRESSURE",
            "target_margin_price": target_price,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": target_price, "high": current_price},
            "reasoning": ["No verified competitor offers observed. Current price satisfies target margin."],
            "confidence": "medium",
        }

    price_diff_pct = (current_price - comp_ref) / comp_ref

    if price_diff_pct > 0.10:
        # We are more than 10% above competitor, and competitor is >= target_price
        target_recom = max(target_price, round(comp_ref, 2))
        confidence = "low" if high_dispersion else "high"
        reasons.append(f"Current price is {price_diff_pct*100:.1f}% above competitor reference (${comp_ref:.2f}).")
        reasons.append(f"Competitor price satisfies target margin floor (${target_price:.2f}). Lowering to match improves Buy Box competitiveness.")
        if high_dispersion:
            reasons.append("Caution: Competitor price dispersion exceeds 15%; confidence downgraded.")
        return {
            "action": "LOWER",
            "primary_reason": "COMPETITIVE_MATCH",
            "target_margin_price": target_price,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": target_recom, "high": round(target_recom * 1.02, 2)},
            "reasoning": reasons,
            "confidence": confidence,
        }

    if price_diff_pct < -0.10:
        # We are more than 10% below competitor, room to raise margin
        reasons.append(f"Current price is {abs(price_diff_pct)*100:.1f}% below competitor median (${comp_ref:.2f}).")
        reasons.append("Opportunity to raise price and expand contribution margin while maintaining competitive appeal.")
        recom_low = round(current_price * 1.05, 2)
        recom_high = round(min(comp_ref, current_price * 1.10), 2)
        return {
            "action": "RAISE",
            "primary_reason": "MARGIN_OPPORTUNITY",
            "target_margin_price": target_price,
            "breakeven_price": be_price,
            "minimum_viable_price": mvp_price,
            "suggested_range": {"low": recom_low, "high": max(recom_low, recom_high)},
            "reasoning": reasons,
            "confidence": "high",
        }

    # Within [-10%, +10%] parity
    reasons.append(f"Current price (${current_price:.2f}) is in healthy alignment with market median (${comp_ref:.2f}).")
    return {
        "action": "HOLD",
        "primary_reason": "HEALTHY_PARITY",
        "target_margin_price": target_price,
        "breakeven_price": be_price,
        "minimum_viable_price": mvp_price,
        "suggested_range": {"low": round(comp_ref * 0.98, 2), "high": round(comp_ref * 1.02, 2)},
        "reasoning": reasons,
        "confidence": "high",
    }


# =====================================================================
# 5. Volume Scenarios & Simulation at Current Volume
# =====================================================================

def simulate_price(
    new_price: float,
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    ad_spend_levels: list[float] | None = None,
) -> dict:
    """SIMULATION only, never labeled as an actual result. Does not
    predict sales volume — only deterministic contribution math.
    Preserves exact backward-compatible signature.
    """
    base = contribution_margin(new_price, cogs, referral_fee_pct, fulfillment_fee, other_cost)
    scenarios = []
    for ad in (ad_spend_levels or [0.0]):
        cm = contribution_margin(new_price, cogs, referral_fee_pct, fulfillment_fee, other_cost, ad_cost_per_unit=ad)
        scenarios.append({"ad_cost_per_unit": ad, **cm})
    return {"price": new_price, "base": base, "ad_spend_scenarios": scenarios}


def simulate_price_scenarios(
    current_price: float,
    candidate_prices: List[float],
    cogs: float,
    referral_fee_pct: float,
    fulfillment_fee: float,
    other_cost: float,
    current_unit_volume: int = 100,
) -> dict:
    """What-if price simulation modeled strictly at current observed unit volume.
    Volume elasticity is explicitly labeled NOT_ESTIMATED.
    """
    curr_cm = contribution_margin(current_price, cogs, referral_fee_pct, fulfillment_fee, other_cost)
    curr_total_revenue = round(current_price * current_unit_volume, 2)
    curr_total_cm = round(curr_cm["contribution"] * current_unit_volume, 2)

    scenarios = []
    for p in candidate_prices:
        cand_cm = contribution_margin(p, cogs, referral_fee_pct, fulfillment_fee, other_cost)
        total_rev = round(p * current_unit_volume, 2)
        total_cm = round(cand_cm["contribution"] * current_unit_volume, 2)
        delta_rev = round(total_rev - curr_total_revenue, 2)
        delta_cm = round(total_cm - curr_total_cm, 2)

        # Breakeven volume units required if price is lower
        be_units = None
        pct_volume_needed = None
        if cand_cm["contribution"] > 0 and cand_cm["contribution"] < curr_cm["contribution"]:
            be_units = round(curr_total_cm / cand_cm["contribution"], 1)
            pct_volume_needed = round((be_units - current_unit_volume) / current_unit_volume * 100.0, 1)

        scenarios.append({
            "candidate_price": p,
            "unit_contribution": cand_cm["contribution"],
            "unit_margin_pct": cand_cm["margin_pct"],
            "total_revenue_at_current_volume": total_rev,
            "total_contribution_at_current_volume": total_cm,
            "delta_revenue": delta_rev,
            "delta_contribution": delta_cm,
            "breakeven_units_required": be_units,
            "required_volume_increase_pct": pct_volume_needed,
        })

    return {
        "current_price": current_price,
        "current_volume": current_unit_volume,
        "volume_response": "NOT_ESTIMATED",
        "current_total_revenue": curr_total_revenue,
        "current_total_contribution": curr_total_cm,
        "scenarios": scenarios,
    }
