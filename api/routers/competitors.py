"""
competitors.py — Competitor Intelligence & Matching Router for CommerceSense AI v3.

Provides:
  1. GET /api/v1/competitors/{product_id} — Direct competitor analysis (Tier 1 & Tier 2)
     with substitutes (Tier 3) strictly segregated.
  2. POST /api/v1/competitors/{product_id}/sync — Prospective snapshot ingestion via
     SP-API getCompetitiveSummary batching.
  3. GET /api/v1/competitors/{product_id}/matches — 3-tier candidate matches and rankings.
  4. POST /api/v1/competitors/{product_id}/matches/{match_id}/review — Human confirmation/rejection.
  5. GET /api/v1/competitors/{product_id}/history — Prospective price history time-series.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import db
import db.intelligence_db as idb
from api.intelligence_common import RunTracker, get_product_or_404
from intelligence.matching_engine import (
    MatchMethod,
    MatchResult,
    MatchTier,
    evaluate_candidate_matches,
)
from intelligence.pricing_engine import (
    filter_direct_competitor_observations,
    price_distribution,
)
from providers.amazon_pricing import (
    fetch_competitive_summary_batch,
)
from providers.provenance import ProvenanceEnvelope, SourceEnvelope

router = APIRouter(prefix="/competitors", tags=["competitor-intelligence"])
logger = logging.getLogger("commerce_sense.competitors_router")


class MatchReviewRequest(BaseModel):
    confirmed: bool = Field(..., description="True to confirm match, False to reject")
    reviewer: str = Field(default="seller", description="Actor who confirmed or rejected")
    reason: Optional[str] = Field(default=None, description="Optional explanation for review")


@router.get("/observations/{product_id}")
@router.get("/{product_id}")
def get_competitor_summary(product_id: str) -> dict:
    """Returns direct competitor intelligence for a product.
    Strict Invariant: Tier 3 substitutes are strictly segregated from direct competitor medians.
    """
    product = get_product_or_404(product_id)
    asin = product.get("asin") or product_id

    # Retrieve all pricing observations from database
    raw_obs = [dict(r) for r in idb.get_pricing_observations(product_id)]

    # Separate into direct competition (Tier 1 & 2) vs substitutes (Tier 3)
    direct_obs = filter_direct_competitor_observations(raw_obs)
    substitutes = [
        o for o in raw_obs
        if o.get("match_tier") in ("TIER_3_SUBSTITUTE", "SUBSTITUTE")
    ]

    current_price = float(product.get("base_price", 0.0))
    dist = price_distribution(
        [o["landed_price"] for o in direct_obs if o.get("landed_price")],
        current_price=current_price,
    )

    # Identify Buy Box Winner among direct competitors
    buy_box_obs = next((o for o in direct_obs if o.get("is_buy_box_winner")), None)
    coverage = idb.get_pricing_snapshot_coverage(product_id)

    payload = {
        "product_id": product_id,
        "asin": asin,
        "current_price": current_price,
        "direct_competitor_distribution": dist,
        "direct_competitor_count": len(direct_obs),
        "substitute_count": len(substitutes),
        "buy_box_offer": buy_box_obs,
        "direct_competitors": direct_obs,
        "substitutes": substitutes,
        "prospective_coverage": coverage,
    }
    envelope = SourceEnvelope.create(
        source_id=f"comp-summary-{product_id}",
        provider="matching-engine",
        source_type=ProvenanceEnvelope.CALCULATED,
        marketplace_id=product.get("marketplace_id", "A21TJRUUN4KGV"),
        currency=product.get("currency", "USD"),
        raw_data=payload,
        limitations=[
            "Substitutes (Tier 3) are strictly excluded from direct competitor median and distribution calculations.",
            "Price history tracked prospectively from first ingestion date.",
        ],
    )
    return {
        "envelope": envelope.model_dump(),
        "envelope_type": envelope.source_type.value,
        "data": payload,
    }


@router.post("/{product_id}/sync")
def sync_competitor_snapshot(product_id: str) -> dict:
    """Ingests fresh prospective competitor snapshots via SP-API getCompetitiveSummary."""
    product = get_product_or_404(product_id)
    asin = product.get("asin") or product_id

    # Fetch batch snapshot
    comp_result = fetch_competitive_summary_batch([asin])
    fresh_obs = comp_result.observations

    # Persist into pricing_observations
    for obs in fresh_obs:
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

    return {
        "synced": True,
        "product_id": product_id,
        "asin": asin,
        "observations_ingested": len(fresh_obs),
        "provenance": comp_result.envelope.source_type.value,
    }


@router.get("/matches/{product_id}")
@router.get("/{product_id}/matches")
def get_competitor_matches(product_id: str) -> dict:
    """Returns candidate competitor matches classified into Tier 1, Tier 2, and Tier 3."""
    product = get_product_or_404(product_id)

    # Check for existing evaluated matches in DB
    existing_matches = [dict(r) for r in idb.get_competitor_matches(product_id)]
    if existing_matches:
        return {
            "product_id": product_id,
            "matches": existing_matches,
            "total_matches": len(existing_matches),
        }

    # Generate candidate matches from other products in the catalog
    all_products = db.get_products()
    candidates = [p for p in all_products if p["product_id"] != product_id]

    evaluated = evaluate_candidate_matches(product, candidates)

    # Persist initial matches
    for m in evaluated:
        idb.insert_competitor_match(
            product_id=product_id,
            candidate_asin=m.candidate_asin,
            candidate_title=m.candidate_title,
            match_tier=m.match_tier.value,
            match_confidence=m.match_confidence,
            match_method=m.match_method.value,
            matched_fields=m.matched_fields,
            mismatched_fields=m.mismatched_fields,
            seller_confirmed=None,
        )

    fresh_matches = [dict(r) for r in idb.get_competitor_matches(product_id)]
    return {
        "product_id": product_id,
        "matches": fresh_matches,
        "total_matches": len(fresh_matches),
    }


@router.post("/matches/{match_id}/review")
@router.post("/{product_id}/matches/{match_id}/review")
def review_competitor_match(match_id: int, body: MatchReviewRequest, product_id: str = "P001") -> dict:
    """Records human-in-the-loop confirmation or rejection of a competitor match."""
    get_product_or_404(product_id)
    now_str = datetime.now(timezone.utc).isoformat()
    idb.update_competitor_match_status(match_id, confirmed=body.confirmed, reviewed_at=now_str)

    return {
        "recorded": True,
        "match_id": match_id,
        "seller_confirmed": body.confirmed,
        "reviewed_at": now_str,
    }


@router.get("/{product_id}/history")
def get_prospective_price_history(product_id: str) -> dict:
    """Returns prospective time-series price snapshots tracked from the first collection date."""
    get_product_or_404(product_id)
    raw_obs = [dict(r) for r in idb.get_pricing_observations(product_id)]
    coverage = idb.get_pricing_snapshot_coverage(product_id)

    return {
        "product_id": product_id,
        "coverage": coverage,
        "history": sorted(raw_obs, key=lambda x: x.get("observed_at", "")),
        "disclaimer": "Price history is prospective starting from the initial collection date; no retroactive Keepa history is fabricated.",
    }
