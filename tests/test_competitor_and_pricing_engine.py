"""
test_competitor_and_pricing_engine.py — Comprehensive Test Suite for Phase 3.

Covers:
  1. Cost-complete Decimal precision calculations.
  2. 3-Tier competitor matching taxonomy with hard variant constraint gates.
  3. Strict exclusion of Tier 3 substitutes from direct medians.
  4. DO_NOT_MATCH guardrails (margin floor, reputation premium, stockout preservation, FBM).
  5. Price spread contradiction handling (>15% dispersion downgrade).
  6. Volume scenarios at current observed volume (volume_response: NOT_ESTIMATED).
  7. SP-API batching, rate limiting, and prospective snapshots.
  8. Competitor and Pricing Intelligence API endpoints.
"""

from __future__ import annotations

import decimal
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from api.main import app
from intelligence.matching_engine import (
    MatchMethod,
    MatchTier,
    classify_competitor_match,
    evaluate_candidate_matches,
)
from intelligence.pricing_engine import (
    breakeven_price,
    classify_price_state,
    contribution_margin,
    cost_complete_fixed_unit_cost,
    evaluate_pricing_decision,
    filter_direct_competitor_observations,
    minimum_viable_price,
    price_distribution,
    recommend_price_range,
    simulate_price_scenarios,
    target_margin_price,
)
from providers.amazon_pricing import (
    fetch_competitive_summary_batch,
    parse_competitive_summary_response,
)
from providers.provenance import ProvenanceEnvelope

client = TestClient(app)


# =====================================================================
# 1. Decimal Precision & Cost-Complete Math
# =====================================================================

def test_cost_complete_fixed_unit_cost():
    fixed = cost_complete_fixed_unit_cost(
        cogs=5.50,
        fulfillment_fee=3.25,
        closing_fee=0.30,
        packaging_cost=0.45,
        inbound_freight=0.60,
        ad_cost_per_unit=1.20,
        returns_allowance=0.35,
        other_cost=0.15,
    )
    # Sum: 5.50 + 3.25 + 0.30 + 0.45 + 0.60 + 1.20 + 0.35 + 0.15 = 11.80
    assert fixed == Decimal("11.8000")


def test_contribution_margin_decimal_precision():
    cm = contribution_margin(
        price=24.99,
        cogs=6.00,
        referral_fee_pct=0.15,
        fulfillment_fee=3.50,
        other_cost=0.50,
        closing_fee=0.30,
        packaging_cost=0.40,
        inbound_freight=0.50,
        ad_cost_per_unit=1.00,
        returns_allowance=0.25,
    )
    # Fixed = 6.00 + 3.50 + 0.50 + 0.30 + 0.40 + 0.50 + 1.00 + 0.25 = 12.45
    # Referral fee = 24.99 * 0.15 = 3.7485 -> 3.75
    # Total VC = 12.45 + 3.7485 = 16.1985 -> 16.20
    # CM = 24.99 - 16.20 = 8.79
    # Margin % = 8.79 / 24.99 = 0.3517 (35.17%)
    assert cm["variable_cost"] == pytest.approx(16.20, abs=0.01)
    assert cm["contribution"] == pytest.approx(8.79, abs=0.01)
    assert cm["margin_pct"] == pytest.approx(0.3517, abs=0.001)


def test_breakeven_and_target_margin_math():
    cogs = 10.0
    ref_fee = 0.15
    fba = 4.0
    other = 1.0
    # Fixed = 15.0
    # Breakeven = 15.0 / (1 - 0.15) = 15.0 / 0.85 = 17.65
    be = breakeven_price(cogs, ref_fee, fba, other)
    assert be == pytest.approx(17.65, abs=0.01)

    # Target Margin (25%) = 15.0 / (1 - 0.15 - 0.25) = 15.0 / 0.60 = 25.00
    tmp = target_margin_price(cogs, ref_fee, fba, other, target_margin_pct=0.25)
    assert tmp == pytest.approx(25.00, abs=0.01)

    # Minimum Viable Price (10% floor) = 15.0 / (1 - 0.15 - 0.10) = 15.0 / 0.75 = 20.00
    mvp = minimum_viable_price(cogs, ref_fee, fba, other, min_margin_pct=0.10)
    assert mvp == pytest.approx(20.00, abs=0.01)
    assert be < mvp < tmp


def test_unreachable_target_margin_returns_none():
    # Referral fee (15%) + Target margin (90%) = 105% > 100% -> unreachable
    res = target_margin_price(cogs=10, referral_fee_pct=0.15, fulfillment_fee=4, other_cost=1, target_margin_pct=0.90)
    assert res is None


# =====================================================================
# 2. 3-Tier Competitor Matching Taxonomy & Variant Constraint Gates
# =====================================================================

def test_tier_1_same_asin_match():
    res = classify_competitor_match(
        target_asin="B07XQXZXJC",
        target_title="Organic Green Tea Bags 100 Count",
        target_brand="PureLeaf",
        candidate_asin="B07XQXZXJC",
        candidate_title="Organic Green Tea Bags 100 Count",
        candidate_brand="PureLeaf",
    )
    assert res.match_tier == MatchTier.TIER_1_SAME_ASIN
    assert res.match_method == MatchMethod.EXACT_ASIN
    assert res.score == 100.0
    assert "asin" in res.matched_fields


def test_tier_2_exact_identifier_barcode_match():
    res = classify_competitor_match(
        target_asin="B07X111111",
        target_title="Stainless Steel Water Bottle 750ml",
        target_brand="HydroSafe",
        candidate_asin="B08Y222222",
        candidate_title="HydroSafe Insulated 750ml Flask",
        candidate_brand="HydroSafe",
        target_identifiers={"gtin": "012345678905"},
        candidate_identifiers={"gtin": "012345678905"},
    )
    assert res.match_tier == MatchTier.TIER_2_EXACT_EQUIVALENT
    assert res.match_method == MatchMethod.IDENTIFIER_GTIN
    assert res.score == 98.0


def test_tier_3_forced_by_pack_count_mismatch():
    # Hard constraint: Pack of 2 vs Pack of 1 MUST be degraded to Tier 3 substitute!
    res = classify_competitor_match(
        target_asin="B07X111111",
        target_title="Pure Silicon Spatula Pack of 2",
        target_brand="ChefCraft",
        candidate_asin="B08Y222222",
        candidate_title="Pure Silicon Spatula Pack of 1",
        candidate_brand="ChefCraft",
    )
    assert res.match_tier == MatchTier.TIER_3_SUBSTITUTE
    assert res.match_method == MatchMethod.SPEC_HARD_CONSTRAINT
    assert any("pack_count" in m for m in res.mismatched_fields)


def test_tier_3_forced_by_size_volume_mismatch():
    # Hard constraint: 500ml vs 250ml MUST be degraded to Tier 3 substitute!
    res = classify_competitor_match(
        target_asin="B07X111111",
        target_title="Extra Virgin Olive Oil 500ml Cold Pressed",
        target_brand="Olivo",
        candidate_asin="B08Y222222",
        candidate_title="Extra Virgin Olive Oil 250ml Cold Pressed",
        candidate_brand="Olivo",
    )
    assert res.match_tier == MatchTier.TIER_3_SUBSTITUTE
    assert res.match_method == MatchMethod.SPEC_HARD_CONSTRAINT
    assert any("size_volume" in m for m in res.mismatched_fields)


def test_filter_direct_competitor_observations_excludes_tier_3():
    observations = [
        {"product_id": "P1", "competitor": "Comp1", "price": 20.0, "landed_price": 20.0, "match_tier": "TIER_1_SAME_ASIN"},
        {"product_id": "P1", "competitor": "Comp2", "price": 22.0, "landed_price": 22.0, "match_tier": "TIER_2_EXACT_EQUIVALENT"},
        {"product_id": "P1", "competitor": "Subst1", "price": 10.0, "landed_price": 10.0, "match_tier": "TIER_3_SUBSTITUTE"},
    ]
    direct = filter_direct_competitor_observations(observations)
    assert len(direct) == 2
    assert all(d["match_tier"] != "TIER_3_SUBSTITUTE" for d in direct)

    # Median calculated on direct observations only: (20 + 22) / 2 = 21.0, NOT including 10.0
    dist = price_distribution([], current_price=21.0, observations=observations)
    assert dist["median"] == 21.0
    assert dist["sample_size"] == 2


# =====================================================================
# 3. DO_NOT_MATCH Guardrails & Floor Protection
# =====================================================================

def test_guardrail_margin_floor_do_not_match():
    # If competitor is $18, but target margin requires $22 -> DO_NOT_MATCH
    decision = evaluate_pricing_decision(
        current_price=25.0,
        cogs=10.0,
        referral_fee_pct=0.15,
        fulfillment_fee=4.0,
        other_cost=1.0,
        target_margin_pct=0.25,  # Requires $25.00
        competitor_median=18.0,
    )
    assert decision["action"] == "DO_NOT_MATCH"
    assert decision["primary_reason"] == "BELOW_MARGIN_FLOOR"
    assert decision["target_margin_price"] == 25.00
    assert any("breaches minimum margin floor" in r for r in decision["reasoning"])


def test_guardrail_reputation_asymmetry_do_not_match():
    # If our rating is 4.6 and competitor is 3.5 -> DO_NOT_MATCH (premium justified)
    decision = evaluate_pricing_decision(
        current_price=25.0,
        cogs=6.0,
        referral_fee_pct=0.15,
        fulfillment_fee=3.0,
        other_cost=1.0,
        target_margin_pct=0.20,  # Requires $16.67
        competitor_median=21.0,  # Below our price, but above target margin
        our_rating=4.6,
        competitor_rating=3.5,
    )
    assert decision["action"] == "DO_NOT_MATCH"
    assert decision["primary_reason"] == "PREMIUM_JUSTIFIED"
    assert any("substantially higher" in r for r in decision["reasoning"])


def test_guardrail_stockout_preservation_do_not_match():
    # If days of cover is < 14 -> DO_NOT_MATCH (holding price to ration stock)
    decision = evaluate_pricing_decision(
        current_price=25.0,
        cogs=6.0,
        referral_fee_pct=0.15,
        fulfillment_fee=3.0,
        other_cost=1.0,
        target_margin_pct=0.20,
        competitor_median=22.0,
        days_of_cover=8,
    )
    assert decision["action"] == "DO_NOT_MATCH"
    assert decision["primary_reason"] == "STOCKOUT_PRESERVATION"
    assert any("critically low" in r for r in decision["reasoning"])


def test_guardrail_unverified_fbm_seller_do_not_match():
    # If competitor is non-Prime FBM -> DO_NOT_MATCH (FBA justifies premium)
    decision = evaluate_pricing_decision(
        current_price=25.0,
        cogs=6.0,
        referral_fee_pct=0.15,
        fulfillment_fee=3.0,
        other_cost=1.0,
        target_margin_pct=0.20,
        competitor_median=22.0,
        is_competitor_fba=False,
    )
    assert decision["action"] == "DO_NOT_MATCH"
    assert decision["primary_reason"] == "UNVERIFIED_SELLER"
    assert any("merchant-fulfilled (FBM)" in r for r in decision["reasoning"])


def test_decision_lower_when_feasible_competitive_pressure():
    # If competitor is $22, our price is $26, and target margin requires $18 -> LOWER
    decision = evaluate_pricing_decision(
        current_price=26.0,
        cogs=7.0,
        referral_fee_pct=0.15,
        fulfillment_fee=3.0,
        other_cost=1.0,
        target_margin_pct=0.20,  # Requires $18.33
        competitor_median=22.0,
    )
    assert decision["action"] == "LOWER"
    assert decision["primary_reason"] == "COMPETITIVE_MATCH"
    assert decision["suggested_range"]["low"] == 22.0


def test_decision_raise_when_margin_opportunity():
    # If competitor is $35, our price is $25, and target margin requires $18 -> RAISE
    decision = evaluate_pricing_decision(
        current_price=25.0,
        cogs=7.0,
        referral_fee_pct=0.15,
        fulfillment_fee=3.0,
        other_cost=1.0,
        target_margin_pct=0.20,
        competitor_median=35.0,
    )
    assert decision["action"] == "RAISE"
    assert decision["primary_reason"] == "MARGIN_OPPORTUNITY"
    assert decision["suggested_range"]["low"] > 25.0


# =====================================================================
# 4. Contradiction & Spread Handling
# =====================================================================

def test_high_dispersion_downgrades_confidence():
    # Prices: $20, $30, $21 -> Spread = (30 - 20) / 21 = 47.6% > 15%
    spread = price_distribution([20.0, 30.0, 21.0], current_price=22.0)
    assert spread["relative_spread"] > 0.15

    recom = recommend_price_range(target_margin_price_value=18.0, median_competitor=spread["median"], price_state="HEALTHY_RANGE", price_spread=spread)
    assert recom["confidence"] == "low"
    assert any("observations disagree" in r for r in recom["reasoning"])


# =====================================================================
# 5. Volume Scenarios (Pricing Lab)
# =====================================================================

def test_simulate_price_scenarios_at_current_volume():
    result = simulate_price_scenarios(
        current_price=25.0,
        candidate_prices=[22.0, 28.0],
        cogs=8.0,
        referral_fee_pct=0.15,
        fulfillment_fee=3.0,
        other_cost=1.0,
        current_unit_volume=100,
    )
    assert result["volume_response"] == "NOT_ESTIMATED"
    assert result["current_volume"] == 100
    assert result["current_total_revenue"] == 2500.0

    scenarios = result["scenarios"]
    assert len(scenarios) == 2

    # Candidate $22 (price drop)
    sc_low = scenarios[0]
    assert sc_low["candidate_price"] == 22.0
    assert sc_low["delta_revenue"] == -300.0  # (22 - 25) * 100
    assert sc_low["delta_contribution"] < 0
    # Requires more units to break even on gross contribution dollars
    assert sc_low["breakeven_units_required"] > 100
    assert sc_low["required_volume_increase_pct"] > 0

    # Candidate $28 (price rise)
    sc_high = scenarios[1]
    assert sc_high["candidate_price"] == 28.0
    assert sc_high["delta_revenue"] == 300.0
    assert sc_high["delta_contribution"] > 0
    assert sc_high["breakeven_units_required"] is None


# =====================================================================
# 6. SP-API Batch Ingestion & Provenance Envelope
# =====================================================================

def test_fetch_competitive_summary_batch_demo_fallback():
    env = fetch_competitive_summary_batch(["B07XQXZXJC", "B08Y222222"])
    assert env.envelope_type == ProvenanceEnvelope.DEMO
    assert len(env.data) >= 2
    # Verify offer fields populated
    first_obs = env.data[0]
    assert "landed_price" in first_obs
    assert "is_buy_box_winner" in first_obs
    assert "match_tier" in first_obs


# =====================================================================
# 7. Competitor & Pricing API Endpoints
# =====================================================================

def test_api_competitors_summary():
    resp = client.get("/api/v1/competitors/P001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["envelope_type"] == "CALCULATED"
    payload = data["data"]
    assert payload["product_id"] == "P001"
    assert "direct_competitor_distribution" in payload
    assert "substitute_count" in payload


def test_api_competitors_sync():
    resp = client.post("/api/v1/competitors/P001/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced"] is True
    assert data["product_id"] == "P001"
    assert data["observations_ingested"] > 0


def test_api_competitors_matches_and_review():
    # 1. Fetch matches
    resp = client.get("/api/v1/competitors/P001/matches")
    assert resp.status_code == 200
    data = resp.json()
    matches = data["matches"]
    assert len(matches) > 0

    first_match_id = matches[0]["id"]

    # 2. Review match
    review_resp = client.post(
        f"/api/v1/competitors/P001/matches/{first_match_id}/review",
        json={"confirmed": True, "reviewer": "test_operator", "reason": "Verified same specs"},
    )
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert review_data["recorded"] is True
    assert review_data["seller_confirmed"] is True


def test_api_pricing_update_costs():
    update_payload = {
        "cogs": 6.50,
        "referral_fee_pct": 0.15,
        "fulfillment_fee": 3.20,
        "closing_fee": 0.30,
        "packaging_cost": 0.40,
        "inbound_freight": 0.50,
        "ad_cost_per_unit": 1.10,
        "returns_allowance": 0.25,
        "other_cost": 0.20,
        "target_margin_pct": 0.25,
        "min_margin_pct": 0.10,
        "currency": "USD",
    }
    resp = client.put("/api/pricing-intelligence/P001/costs", json=update_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] is True
    assert data["target_margin_price"] is not None
    assert data["decision"]["action"] in ("HOLD", "LOWER", "RAISE", "MATCH", "DO_NOT_MATCH")


def test_api_pricing_simulate_with_volume_scenario():
    resp = client.post(
        "/api/pricing-intelligence/P001/simulate",
        json={"new_price": 21.99, "ad_spend_levels": [0, 1.5, 3.0]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["simulation"] is True
    assert "volume_scenario" in data
    assert data["volume_scenario"]["volume_response"] == "NOT_ESTIMATED"

