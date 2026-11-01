from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api import deps  # noqa: F401
from api.intelligence_common import RunTracker, explain_or_degrade, get_product_or_404
from api.schemas import IntelligenceApproveRequest, PricingAnalyzeRequest, PricingSimulateRequest

import db
import db.intelligence_db as idb
from decision_log import log_decision
from intelligence.pricing_engine import (
    breakeven_price,
    classify_price_state,
    contribution_margin,
    evaluate_pricing_decision,
    filter_direct_competitor_observations,
    minimum_viable_price,
    price_distribution,
    recommend_price_range,
    simulate_price,
    simulate_price_scenarios,
    target_margin_price,
)

router = APIRouter(tags=["pricing-intelligence"])

_PRICE_PATTERN = re.compile(r"\$\s?\d{1,5}(?:\.\d{2})?")


class PricingCostUpdateRequest(BaseModel):
    cogs: float = Field(..., ge=0, description="Cost of Goods Sold")
    referral_fee_pct: float = Field(..., ge=0, le=1.0, description="Amazon Referral Fee percentage (0.15 = 15%)")
    fulfillment_fee: float = Field(..., ge=0, description="FBA Fulfillment Fee")
    closing_fee: float = Field(default=0.0, ge=0, description="Amazon closing fee")
    packaging_cost: float = Field(default=0.0, ge=0, description="Packaging & prep cost per unit")
    inbound_freight: float = Field(default=0.0, ge=0, description="Inbound freight per unit")
    ad_cost_per_unit: float = Field(default=0.0, ge=0, description="Attributed ad cost per unit")
    returns_allowance: float = Field(default=0.0, ge=0, description="Returns & refund allowance")
    other_cost: float = Field(default=0.0, ge=0, description="Other direct unit costs")
    target_margin_pct: float = Field(..., ge=0, le=1.0, description="Target Contribution Margin percentage")
    min_margin_pct: float = Field(default=0.10, ge=0, le=1.0, description="Minimum Viable Margin percentage floor")
    currency: str = Field(default="USD", description="Currency code")


class ExtendedSimulateRequest(BaseModel):
    new_price: float = Field(..., gt=0, description="Candidate selling price to evaluate")
    ad_spend_levels: Optional[List[float]] = Field(default=None, description="Ad spend levels for sensitivity testing")
    candidate_prices: Optional[List[float]] = Field(default=None, description="Additional candidate prices for volume scenarios")
    current_unit_volume: int = Field(default=100, ge=1, description="Current unit sales volume (zero elasticity baseline)")


class _PricingExplanation(BaseModel):
    interpretation: str
    trade_offs: str
    confidence: Literal["none", "low", "medium", "high"]


def _analyze(product_id: str) -> dict:
    pricing = idb.get_pricing_data(product_id)
    if pricing is None:
        raise HTTPException(status_code=422, detail="No pricing cost data available for this product.")
    products = {p["product_id"]: p for p in db.get_products()}
    current_price = products[product_id]["base_price"]

    pricing_dict = dict(pricing)
    cogs = pricing_dict["cogs"]
    referral_fee_pct = pricing_dict["referral_fee_pct"]
    fulfillment_fee = pricing_dict["fulfillment_fee"]
    other_cost = pricing_dict["other_cost"]
    target_margin_pct = pricing_dict["target_margin_pct"]
    min_margin_pct = pricing_dict.get("min_margin_pct", 0.10)
    closing_fee = pricing_dict.get("closing_fee", 0.0)
    packaging_cost = pricing_dict.get("packaging_cost", 0.0)
    inbound_freight = pricing_dict.get("inbound_freight", 0.0)
    ad_cost_per_unit = pricing_dict.get("ad_cost_per_unit", 0.0)
    returns_allowance = pricing_dict.get("returns_allowance", 0.0)

    # Deterministic Decimal Contribution & Breakeven
    cm = contribution_margin(
        current_price, cogs, referral_fee_pct, fulfillment_fee, other_cost,
        ad_cost_per_unit=ad_cost_per_unit, closing_fee=closing_fee,
        packaging_cost=packaging_cost, inbound_freight=inbound_freight,
        returns_allowance=returns_allowance,
    )
    be = breakeven_price(
        cogs, referral_fee_pct, fulfillment_fee, other_cost,
        closing_fee=closing_fee, packaging_cost=packaging_cost,
        inbound_freight=inbound_freight, ad_cost_per_unit=ad_cost_per_unit,
        returns_allowance=returns_allowance,
    )
    tmp = target_margin_price(
        cogs, referral_fee_pct, fulfillment_fee, other_cost, target_margin_pct,
        closing_fee=closing_fee, packaging_cost=packaging_cost,
        inbound_freight=inbound_freight, ad_cost_per_unit=ad_cost_per_unit,
        returns_allowance=returns_allowance,
    )
    mvp = minimum_viable_price(
        cogs, referral_fee_pct, fulfillment_fee, other_cost, min_margin_pct=min_margin_pct,
        closing_fee=closing_fee, packaging_cost=packaging_cost,
        inbound_freight=inbound_freight, ad_cost_per_unit=ad_cost_per_unit,
        returns_allowance=returns_allowance,
    )

    raw_observations = [dict(o) for o in idb.get_pricing_observations(product_id)]
    # Segregate Tier 1 & 2 direct competitors from Tier 3 substitutes
    direct_observations = filter_direct_competitor_observations(raw_observations)
    dist = price_distribution(
        [o["landed_price"] if o.get("landed_price") else o["price"] for o in direct_observations],
        current_price=current_price,
    )

    state = classify_price_state(cm["margin_pct"], target_margin_pct, current_price, dist["median"])
    legacy_recommendation = recommend_price_range(tmp, dist["median"], state, price_spread=dist)

    # Buy Box observation among direct competitors
    buy_box_obs = next((o for o in direct_observations if o.get("is_buy_box_winner")), None)
    bb_price = buy_box_obs.get("landed_price") if buy_box_obs else None

    # Comprehensive Decision Policy Engine
    decision = evaluate_pricing_decision(
        current_price=current_price,
        cogs=cogs,
        referral_fee_pct=referral_fee_pct,
        fulfillment_fee=fulfillment_fee,
        other_cost=other_cost,
        target_margin_pct=target_margin_pct,
        min_margin_pct=min_margin_pct,
        competitor_median=dist["median"],
        buy_box_price=bb_price,
        price_distribution_result=dist,
    )

    coverage = idb.get_pricing_snapshot_coverage(product_id)

    return {
        "product_id": product_id,
        "current_price": current_price,
        "cost_inputs": pricing_dict,
        "contribution": cm,
        "breakeven_price": be,
        "target_margin_price": tmp,
        "minimum_viable_price": mvp,
        "price_distribution": dist,
        "observations": raw_observations,
        "direct_competitor_count": len(direct_observations),
        "price_state": state,
        "recommendation": legacy_recommendation,
        "decision": decision,
        "coverage": coverage,
    }


@router.get("/pricing-intelligence/{product_id}")
def get_pricing_intelligence(product_id: str) -> dict:
    get_product_or_404(product_id)
    return {"provenance": "CALCULATED", **_analyze(product_id)}


@router.put("/pricing-intelligence/{product_id}/costs")
def update_pricing_costs(product_id: str, body: PricingCostUpdateRequest) -> dict:
    """Updates unit economics and margin thresholds for a product."""
    get_product_or_404(product_id)
    idb.upsert_pricing_data(
        product_id=product_id,
        cogs=body.cogs,
        referral_fee_pct=body.referral_fee_pct,
        fulfillment_fee=body.fulfillment_fee,
        other_cost=body.other_cost,
        target_margin_pct=body.target_margin_pct,
        currency=body.currency,
        closing_fee=body.closing_fee,
        packaging_cost=body.packaging_cost,
        inbound_freight=body.inbound_freight,
        ad_cost_per_unit=body.ad_cost_per_unit,
        returns_allowance=body.returns_allowance,
        min_margin_pct=body.min_margin_pct,
    )
    analysis = _analyze(product_id)
    return {"updated": True, "product_id": product_id, **analysis}


@router.post("/pricing-intelligence/{product_id}/analyze")
def analyze_pricing(product_id: str, body: PricingAnalyzeRequest) -> dict:
    product = get_product_or_404(product_id)
    provenance = "CALCULATED"

    if body.use_live_research:
        from providers.amazon_pricing import fetch_competitive_summary_batch

        with RunTracker(product_id, "pricing", "LIVE"):
            asin = product.get("asin") or product_id
            env = fetch_competitive_summary_batch([asin])
            for obs in env.data:
                idb.insert_pricing_observation(
                    product_id=product_id,
                    competitor=obs.get("competitor", "Marketplace Competitor"),
                    price=float(obs.get("price", 0.0)),
                    currency=obs.get("currency", "USD"),
                    source=obs.get("source", "AMAZON_OFFICIAL"),
                    source_url=obs.get("source_url"),
                    observed_at=obs.get("observed_at", datetime.now(timezone.utc).isoformat()),
                    confidence=obs.get("confidence", "high"),
                    is_verified=obs.get("is_verified", False),
                    competitor_asin=obs.get("competitor_asin"),
                    shipping_cost=float(obs.get("shipping_cost", 0.0)),
                    landed_price=float(obs.get("landed_price", 0.0)),
                    match_tier=obs.get("match_tier", "TIER_1_SAME_ASIN"),
                    is_buy_box_winner=obs.get("is_buy_box_winner", False),
                    fulfillment_channel=obs.get("fulfillment_channel", "FBA"),
                    condition_type=obs.get("condition_type", "New"),
                    seller_rating=float(obs.get("seller_rating", 4.0)) if obs.get("seller_rating") else None,
                )
            provenance = env.envelope_type.value
    else:
        with RunTracker(product_id, "pricing", "SYNTHETIC"):
            pass

    analysis = _analyze(product_id)
    idb.insert_pricing_analysis(
        product_id, analysis["current_price"], analysis["contribution"]["variable_cost"],
        analysis["contribution"]["contribution"], analysis["contribution"]["margin_pct"] or 0,
        analysis["breakeven_price"] or 0, analysis["target_margin_price"] or 0, analysis["price_state"],
        analysis["recommendation"]["low"], analysis["recommendation"]["high"],
        datetime.now(timezone.utc).isoformat(),
    )

    prompt = (
        f"Current price: ${analysis['current_price']}. Margin: {analysis['contribution']['margin_pct']}. "
        f"Price state: {analysis['price_state']}. Recommended action: {analysis['decision']['action']} ({analysis['decision']['primary_reason']}). "
        f"Suggested range: {analysis['recommendation']['low']}-{analysis['recommendation']['high']}. "
        f"Reasoning already computed: {analysis['recommendation']['reasoning']}. "
        "In 2-3 sentences, interpret this for the seller and summarize the trade-offs. Do not invent numbers not given."
    )
    explanation = explain_or_degrade(
        "You are a pricing analyst. Base your explanation only on the facts given -- never invent numbers.",
        prompt, _PricingExplanation,
        agent="pricing_intelligence", product_name=product["name"],
    )
    log_decision(agent="pricing_intelligence", product_name=product["name"], action="analyzed",
                 detail={"action": analysis["decision"]["action"], "price_state": analysis["price_state"], "margin_pct": analysis["contribution"]["margin_pct"]})
    return {"provenance": provenance, **analysis, "ai_explanation": explanation}


@router.post("/pricing-intelligence/{product_id}/simulate")
def simulate(product_id: str, body: PricingSimulateRequest) -> dict:
    product = get_product_or_404(product_id)
    pricing = idb.get_pricing_data(product_id)
    if pricing is None:
        raise HTTPException(status_code=422, detail="No pricing cost data available for this product.")

    pricing_dict = dict(pricing)
    with RunTracker(product_id, "pricing", "SYNTHETIC"):
        legacy_result = simulate_price(
            body.new_price, pricing_dict["cogs"], pricing_dict["referral_fee_pct"],
            pricing_dict["fulfillment_fee"], pricing_dict["other_cost"], body.ad_spend_levels,
        )
        volume_scenarios = simulate_price_scenarios(
            current_price=product["base_price"],
            candidate_prices=[body.new_price],
            cogs=pricing_dict["cogs"],
            referral_fee_pct=pricing_dict["referral_fee_pct"],
            fulfillment_fee=pricing_dict["fulfillment_fee"],
            other_cost=pricing_dict["other_cost"],
            current_unit_volume=100,
        )

    log_decision(agent="pricing_intelligence", product_name=product["name"], action="simulation_executed",
                 detail={"new_price": body.new_price, "margin_pct": legacy_result.get("base", {}).get("margin_pct")})
    return {
        "provenance": "CALCULATED",
        "simulation": True,
        "product_id": product_id,
        **legacy_result,
        "volume_scenario": volume_scenarios,
    }


@router.post("/pricing-intelligence/{product_id}/approve")
def approve_pricing(product_id: str, body: IntelligenceApproveRequest) -> dict:
    product = get_product_or_404(product_id)
    action = f"decision_{body.decision}"
    log_decision(agent="human", product_name=product["name"], action=action,
                 detail={"module": "pricing", "field": body.field, "reason": body.reason, "decided_by": body.decided_by})
    return {"recorded": True, "action": action}


@router.get("/pricing-intelligence/{product_id}/history")
def pricing_history(product_id: str) -> dict:
    get_product_or_404(product_id)
    return {
        "runs": [dict(r) for r in idb.get_intelligence_runs(module="pricing", product_id=product_id)],
        "analyses": [dict(r) for r in idb.get_pricing_analysis_history(product_id)],
    }
