from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import deps  # noqa: F401
from api.intelligence_common import RunTracker, explain_or_degrade, get_product_or_404
from api.schemas import IntelligenceApproveRequest, PricingAnalyzeRequest, PricingSimulateRequest

import db
import intelligence_db as idb
from decision_log import log_decision
from pricing_engine import (
    breakeven_price,
    classify_price_state,
    contribution_margin,
    price_distribution,
    recommend_price_range,
    simulate_price,
    target_margin_price,
)

router = APIRouter(tags=["pricing-intelligence"])

_PRICE_PATTERN = re.compile(r"\$\s?\d{1,5}(?:\.\d{2})?")


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

    cm = contribution_margin(current_price, pricing["cogs"], pricing["referral_fee_pct"], pricing["fulfillment_fee"], pricing["other_cost"])
    be = breakeven_price(pricing["cogs"], pricing["referral_fee_pct"], pricing["fulfillment_fee"], pricing["other_cost"])
    tmp = target_margin_price(pricing["cogs"], pricing["referral_fee_pct"], pricing["fulfillment_fee"], pricing["other_cost"], pricing["target_margin_pct"])

    observations = idb.get_pricing_observations(product_id)
    obs_prices = [o["price"] for o in observations]
    dist = price_distribution(obs_prices, current_price)

    state = classify_price_state(cm["margin_pct"], pricing["target_margin_pct"], current_price, dist["median"])
    recommendation = recommend_price_range(tmp, dist["median"], state, price_spread=dist)

    return {
        "product_id": product_id,
        "current_price": current_price,
        "cost_inputs": dict(pricing),
        "contribution": cm,
        "breakeven_price": be,
        "target_margin_price": tmp,
        "price_distribution": dist,
        "observations": [dict(o) for o in observations],
        "price_state": state,
        "recommendation": recommendation,
    }


@router.get("/pricing-intelligence/{product_id}")
def get_pricing_intelligence(product_id: str) -> dict:
    get_product_or_404(product_id)
    return {"provenance": "SYNTHETIC", **_analyze(product_id)}


@router.post("/pricing-intelligence/{product_id}/analyze")
def analyze_pricing(product_id: str, body: PricingAnalyzeRequest) -> dict:
    product = get_product_or_404(product_id)
    provenance = "SYNTHETIC"

    if body.use_live_research:
        from providers.websearch import research_competitor_prices

        with RunTracker(product_id, "pricing", "LIVE"):
            bundle = research_competitor_prices(product["name"])
            idb.clear_pricing_observations_by_source(product_id, "web")
            for finding in bundle.findings:
                for match in _PRICE_PATTERN.findall(finding.snippet):
                    price = float(match.replace("$", "").replace(" ", ""))
                    idb.insert_pricing_observation(
                        product_id, "Web observation", price, "USD", "web",
                        finding.source_url, datetime.now(timezone.utc).isoformat(), "low", False,
                    )
            provenance = "LIVE"
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
        f"Price state: {analysis['price_state']}. Recommended range: {analysis['recommendation']['low']}-{analysis['recommendation']['high']}. "
        f"Reasoning already computed: {analysis['recommendation']['reasoning']}. "
        "In 2-3 sentences, interpret this for the seller and summarize the trade-offs. Do not invent numbers not given."
    )
    explanation = explain_or_degrade(
        "You are a pricing analyst. Base your explanation only on the facts given -- never invent numbers.",
        prompt, _PricingExplanation,
        agent="pricing_intelligence", product_name=product["name"],
    )
    log_decision(agent="pricing_intelligence", product_name=product["name"], action="analyzed",
                 detail={"price_state": analysis["price_state"], "margin_pct": analysis["contribution"]["margin_pct"]})
    return {"provenance": provenance, **analysis, "ai_explanation": explanation}


@router.post("/pricing-intelligence/{product_id}/simulate")
def simulate(product_id: str, body: PricingSimulateRequest) -> dict:
    product = get_product_or_404(product_id)
    pricing = idb.get_pricing_data(product_id)
    if pricing is None:
        raise HTTPException(status_code=422, detail="No pricing cost data available for this product.")
    result = simulate_price(body.new_price, pricing["cogs"], pricing["referral_fee_pct"], pricing["fulfillment_fee"],
                             pricing["other_cost"], body.ad_spend_levels)
    log_decision(agent="pricing_intelligence", product_name=product["name"], action="simulation_executed",
                 detail={"new_price": body.new_price, "margin_pct": result.get("margin_pct")})
    return {"provenance": "SYNTHETIC", "simulation": True, "product_id": product_id, **result}


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
