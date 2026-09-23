"""
opportunity.py — Product Bundle View: synthesizes listing/pricing/review/
inventory health + existing signals into one Attention Score via the
Commerce Opportunity Engine. Entirely deterministic and cheap (no LLM, no
network) — safe to call for every product without a human trigger, unlike
the LLM-explanation/rewrite/live-research endpoints in the other routers.
"""

from __future__ import annotations

import json

from fastapi import APIRouter

from api import deps  # noqa: F401
from api.intelligence_common import get_product_or_404

import db
import intelligence_db as idb
from inventory_engine import classify_inventory, compute_demand, days_of_cover, reorder_point
from listing_engine import evaluate_listing, score_listing
from opportunity_engine import compute_attention_score
from pricing_engine import classify_price_state, contribution_margin, price_distribution
from review_engine import detect_emerging_issues, discover_candidate_words, rating_stats, themes_for_category

router = APIRouter(tags=["opportunity"])


def _listing_score(product_id: str) -> int | None:
    row = idb.get_listing_data(product_id)
    if row is None:
        return None
    d = dict(row)
    rules = evaluate_listing(
        title=d["title"], brand=d["brand"], product_type=d["product_type"],
        bullets=json.loads(d["bullets"]), description=d["description"],
        attributes=json.loads(d["attributes"]), image_count=d["image_count"],
        image_urls=json.loads(d["image_urls"]),
    )
    return score_listing(rules)["score"]


def _pricing_state(product_id: str, current_price: float) -> str:
    pricing = idb.get_pricing_data(product_id)
    if pricing is None:
        return "UNKNOWN"
    cm = contribution_margin(current_price, pricing["cogs"], pricing["referral_fee_pct"], pricing["fulfillment_fee"], pricing["other_cost"])
    obs = [o["price"] for o in idb.get_pricing_observations(product_id)]
    dist = price_distribution(obs, current_price)
    return classify_price_state(cm["margin_pct"], pricing["target_margin_pct"], current_price, dist["median"])


def _review_signals(product_id: str, category: str) -> tuple[float | None, bool]:
    reviews = [dict(r) for r in idb.get_review_items(product_id)]
    stats = rating_stats(reviews)
    candidate_themes = themes_for_category(category) + discover_candidate_words(reviews, top_n=6)
    has_emerging = any(detect_emerging_issues(reviews, t) for t in candidate_themes)
    return stats["negative_pct"], has_emerging


def _inventory_category(product_id: str) -> str:
    metrics = db.get_metrics_for_product(product_id)
    daily_units = [m["units_sold"] for m in metrics]
    current_inventory = metrics[-1]["inventory_level"] if metrics else 0
    demand = compute_demand(daily_units)
    dc = days_of_cover(current_inventory, demand["weighted_avg"])
    rp = reorder_point(demand["weighted_avg"], 14, 5)
    return classify_inventory(dc, demand["weighted_avg"], current_inventory, rp)


@router.get("/products/{product_id}/intelligence")
def get_product_intelligence(product_id: str) -> dict:
    product = get_product_or_404(product_id)
    category = product["category"]

    listing_score = _listing_score(product_id)
    price_state = _pricing_state(product_id, product["base_price"])
    negative_pct, has_emerging = _review_signals(product_id, category)
    inventory_category = _inventory_category(product_id)
    existing_signals = [dict(s) for s in db.get_detected_signals(product_id)]

    opportunity = compute_attention_score(
        inventory_category=inventory_category, negative_review_pct=negative_pct,
        has_emerging_review_issue=has_emerging, listing_score=listing_score,
        price_state=price_state, existing_signals=existing_signals,
    )

    top_issues: list[str] = []
    if inventory_category in ("STOCKOUT_RISK", "LOW_COVER"):
        top_issues.append(f"Inventory: {inventory_category.replace('_', ' ').title()}")
    if has_emerging:
        top_issues.append("Reviews: emerging complaint theme detected")
    if price_state == "BELOW_MARGIN_FLOOR":
        top_issues.append("Pricing: below target margin floor")
    if listing_score is not None and listing_score < 70:
        top_issues.append(f"Listing: health score {listing_score}/100")
    for s in existing_signals[:2]:
        top_issues.append(f"Signal: {s['signal_type'].replace('_', ' ').title()} ({s['severity']})")

    return {
        "provenance": "SYNTHETIC",
        "product": product,
        "attention_score": opportunity["attention_score"],
        "components": opportunity["components"],
        "listing_score": listing_score,
        "price_state": price_state,
        "inventory_category": inventory_category,
        "review_negative_pct": negative_pct,
        "review_has_emerging_issue": has_emerging,
        "existing_signal_count": len(existing_signals),
        "top_issues": top_issues[:5],
    }
