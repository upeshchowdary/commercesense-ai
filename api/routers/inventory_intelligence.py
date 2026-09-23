from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from api import deps  # noqa: F401
from api.intelligence_common import RunTracker, explain_or_degrade, get_product_or_404
from api.schemas import IntelligenceApproveRequest, InventoryForecastRequest, InventorySimulateRequest

import db
import intelligence_db as idb
from decision_log import log_decision
from inventory_engine import (
    classify_inventory,
    compute_demand,
    days_of_cover,
    excess_inventory_estimate,
    forecast_inventory,
    projected_stockout_date,
    reorder_point,
    safety_stock,
    suggested_reorder_quantity,
    what_if_scenario,
)

router = APIRouter(tags=["inventory-intelligence"])


class _InventoryExplanation(BaseModel):
    diagnosis: str
    confidence: Literal["none", "low", "medium", "high"]


def _analyze(product_id: str) -> dict:
    metrics = db.get_metrics_for_product(product_id)
    daily_units = [m["units_sold"] for m in metrics]
    current_inventory = metrics[-1]["inventory_level"] if metrics else 0

    demand = compute_demand(daily_units)
    cfg = idb.get_inventory_config(product_id)
    lead_time_days = cfg["lead_time_days"] if cfg else 14
    safety_days = cfg["safety_days"] if cfg else 5
    moq = cfg["moq"] if cfg else None
    reorder_multiple = cfg["reorder_multiple"] if cfg else None

    avg = demand["weighted_avg"]
    dc = days_of_cover(current_inventory, avg)
    rp = reorder_point(avg, lead_time_days, safety_days)
    ss = safety_stock(avg, safety_days)
    category = classify_inventory(dc, avg, current_inventory, rp)

    return {
        "product_id": product_id,
        "current_inventory": current_inventory,
        "demand": demand,
        "config": {"lead_time_days": lead_time_days, "safety_days": safety_days, "moq": moq, "reorder_multiple": reorder_multiple},
        "days_of_cover": dc,
        "reorder_point": rp,
        "safety_stock": ss,
        "category": category,
        "suggested_reorder_quantity": suggested_reorder_quantity(avg, current_inventory, moq=moq, reorder_multiple=reorder_multiple),
        "projected_stockout_date": projected_stockout_date(current_inventory, avg),
        "excess_inventory": excess_inventory_estimate(current_inventory, avg, dc),
        "data_sufficient": len(daily_units) > 0,
    }


@router.get("/inventory-intelligence/{product_id}")
def get_inventory_intelligence(product_id: str) -> dict:
    get_product_or_404(product_id)
    return {"provenance": "SYNTHETIC", **_analyze(product_id)}


@router.post("/inventory-intelligence/{product_id}/analyze")
def analyze_inventory(product_id: str) -> dict:
    product = get_product_or_404(product_id)
    with RunTracker(product_id, "inventory", "SYNTHETIC"):
        analysis = _analyze(product_id)

    prompt = (
        f"Product: {product['name']}. Days of cover: {analysis['days_of_cover']}. "
        f"Category: {analysis['category']}. Suggested reorder quantity: {analysis['suggested_reorder_quantity']}. "
        f"Current inventory: {analysis['current_inventory']}. Weighted avg daily demand: {analysis['demand']['weighted_avg']}. "
        "In 2-3 sentences, explain what this means for the seller and why, using only these facts."
    )
    explanation = explain_or_degrade(
        "You are an inventory analyst. Base your explanation only on the facts given -- never invent numbers.",
        prompt, _InventoryExplanation,
    )
    log_decision(agent="inventory_intelligence", product_name=product["name"], action="analyzed",
                 detail={"category": analysis["category"], "days_of_cover": analysis["days_of_cover"]})
    return {"provenance": "SYNTHETIC", **analysis, "ai_explanation": explanation}


@router.post("/inventory-intelligence/{product_id}/forecast")
def forecast(product_id: str, body: InventoryForecastRequest) -> dict:
    get_product_or_404(product_id)
    analysis = _analyze(product_id)
    inbound = [item.model_dump() for item in body.inbound]
    rows = forecast_inventory(analysis["current_inventory"], analysis["demand"]["weighted_avg"], body.days_ahead, inbound)
    return {"provenance": "SYNTHETIC", "product_id": product_id, "rows": rows}


@router.post("/inventory-intelligence/{product_id}/simulate")
def simulate(product_id: str, body: InventorySimulateRequest) -> dict:
    get_product_or_404(product_id)
    analysis = _analyze(product_id)
    lead_time = body.lead_time_days or analysis["config"]["lead_time_days"]
    result = what_if_scenario(analysis["current_inventory"], analysis["demand"]["weighted_avg"], body.reorder_quantity, lead_time)
    return {"provenance": "SYNTHETIC", "simulation": True, "product_id": product_id, **result}


@router.post("/inventory-intelligence/{product_id}/approve")
def approve_inventory(product_id: str, body: IntelligenceApproveRequest) -> dict:
    product = get_product_or_404(product_id)
    action = f"decision_{body.decision}"
    log_decision(agent="human", product_name=product["name"], action=action,
                 detail={"module": "inventory", "field": body.field, "reason": body.reason, "decided_by": body.decided_by})
    return {"recorded": True, "action": action}


@router.get("/inventory-intelligence/{product_id}/history")
def inventory_history(product_id: str) -> list[dict]:
    get_product_or_404(product_id)
    return [dict(r) for r in idb.get_intelligence_runs(module="inventory", product_id=product_id)]
