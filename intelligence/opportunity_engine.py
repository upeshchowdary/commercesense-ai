"""
opportunity_engine.py — the Commerce Opportunity Engine: a deterministic,
fully-itemized aggregation of listing/pricing/review/inventory health plus
the existing synthetic signals into one per-product "Attention Score."
Never an opaque AI score — every point is attributable to a named
component, computed the same way every time for the same inputs.
"""

from __future__ import annotations

_INVENTORY_RISK_POINTS = {
    "STOCKOUT_RISK": 30, "LOW_COVER": 20, "SLOW_MOVING": 10,
    "OVERSTOCK": 8, "HEALTHY": 0, "NO_DATA": 0,
}
_PRICING_PRESSURE_POINTS = {
    "BELOW_MARGIN_FLOOR": 15, "ABOVE_COMPETITIVE_RANGE": 8,
    "COMPETITIVE_PRESSURE": 6, "HEALTHY_RANGE": 0, "UNKNOWN": 0,
}


def inventory_risk_points(inventory_category: str) -> int:
    return _INVENTORY_RISK_POINTS.get(inventory_category, 0)


def review_risk_points(negative_pct: float | None, has_emerging_issue: bool) -> int:
    if negative_pct is None:
        return 0
    score = 0
    if negative_pct >= 30:
        score += 15
    elif negative_pct >= 15:
        score += 8
    if has_emerging_issue:
        score += 10
    return min(score, 25)


def listing_issue_points(listing_score: int | None) -> int:
    if listing_score is None:
        return 0
    if listing_score >= 80:
        return 0
    if listing_score >= 60:
        return 8
    if listing_score >= 40:
        return 14
    return 20


def pricing_pressure_points(price_state: str) -> int:
    return _PRICING_PRESSURE_POINTS.get(price_state, 0)


def existing_signal_points(signals: list[dict]) -> int:
    score = sum(6 if s.get("severity") == "high" else 3 for s in signals)
    return min(score, 10)


def compute_attention_score(
    inventory_category: str,
    negative_review_pct: float | None,
    has_emerging_review_issue: bool,
    listing_score: int | None,
    price_state: str,
    existing_signals: list[dict],
) -> dict:
    components = {
        "inventory_risk": inventory_risk_points(inventory_category),
        "review_risk": review_risk_points(negative_review_pct, has_emerging_review_issue),
        "listing_issues": listing_issue_points(listing_score),
        "pricing_pressure": pricing_pressure_points(price_state),
        "existing_signals": existing_signal_points(existing_signals),
    }
    total = min(sum(components.values()), 100)
    return {"attention_score": total, "components": components}
