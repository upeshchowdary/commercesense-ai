from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import deps  # noqa: F401
from api.intelligence_common import RunTracker, explain_or_degrade, get_product_or_404
from api.schemas import IntelligenceApproveRequest, ListingRewriteRequest

import intelligence_db as idb
from decision_log import log_decision
from listing_engine import check_rewrite_grounding, evaluate_listing, score_listing

router = APIRouter(tags=["listing-intelligence"])


class _ListingDiagnosis(BaseModel):
    diagnosis: str
    top_issue_1: str
    top_issue_2: str
    top_issue_3: str
    confidence: Literal["none", "low", "medium", "high"]


class _TitleRewrite(BaseModel):
    proposed_title: str
    changes: list[str]


def _get_listing_or_422(product_id: str) -> dict:
    row = idb.get_listing_data(product_id)
    if row is None:
        raise HTTPException(status_code=422, detail="No listing data available for this product. Import via CSV or regenerate demo data.")
    d = dict(row)
    d["bullets"] = json.loads(d["bullets"])
    d["attributes"] = json.loads(d["attributes"])
    d["image_urls"] = json.loads(d["image_urls"])
    return d


def _score(product_id: str) -> dict:
    listing = _get_listing_or_422(product_id)
    rules = evaluate_listing(
        title=listing["title"], brand=listing["brand"], product_type=listing["product_type"],
        bullets=listing["bullets"], description=listing["description"],
        attributes=listing["attributes"], image_count=listing["image_count"], image_urls=listing["image_urls"],
    )
    result = score_listing(rules)
    return {"listing": listing, **result}


@router.get("/listing-intelligence/{product_id}")
def get_listing_intelligence(product_id: str) -> dict:
    get_product_or_404(product_id)
    return {"provenance": "SYNTHETIC", "product_id": product_id, **_score(product_id)}


@router.post("/listing-intelligence/{product_id}/analyze")
def analyze_listing(product_id: str) -> dict:
    product = get_product_or_404(product_id)
    with RunTracker(product_id, "listing", "SYNTHETIC"):
        result = _score(product_id)

    idb.insert_listing_audit(
        product_id, result["score"], result["category_scores"], result["failed_rules"],
        result["warnings"], result["passed_rules"], datetime.now(timezone.utc).isoformat(),
    )

    prompt = (
        f"Listing health score: {result['score']}/100. Category scores: {result['category_scores']}. "
        f"Failed checks: {result['failed_rules']}. Warnings: {result['warnings']}. "
        "Give a plain-English diagnosis and the top 3 issues, in order of importance. "
        "If fewer than 3 real issues exist, repeat the most important one. Base this only on the facts given -- "
        "if information is insufficient for a category, say so rather than inventing a reason."
    )
    explanation = explain_or_degrade(
        "You are a listing quality diagnostician for an Amazon seller tool. Never invent facts not in the data given.",
        prompt, _ListingDiagnosis,
        agent="listing_intelligence", product_name=product["name"],
    )
    log_decision(agent="listing_intelligence", product_name=product["name"], action="analyzed",
                 detail={"score": result["score"], "failed_rules": result["failed_rules"]})
    return {"provenance": "SYNTHETIC", "product_id": product_id, **result, "ai_diagnosis": explanation}


@router.post("/listing-intelligence/{product_id}/rewrite")
def rewrite_listing(product_id: str, body: ListingRewriteRequest) -> dict:
    product = get_product_or_404(product_id)
    listing = _get_listing_or_422(product_id)

    original_fields = {
        "title": listing["title"], "bullets": " ".join(listing["bullets"]), "description": listing["description"],
        "attributes": json.dumps(listing["attributes"]),
    }

    if not body.use_ai:
        return {"provenance": "SYNTHETIC", "product_id": product_id, "proposed": None,
                "message": "AI rewrite not requested."}

    with RunTracker(product_id, "listing", "LIVE"):
        prompt = (
            f"Current title: {listing['title']!r}. Brand: {listing['brand']}. Product type: {listing['product_type']}. "
            f"Bullets: {listing['bullets']}. Description: {listing['description']}. "
            "Propose an improved title that is clearer and better structured. Do NOT invent any dimension, material, "
            "certification, quantity, or claim that is not already present in the fields above -- only rephrase and "
            "clarify what's already there. List the specific changes you made."
        )
        result = explain_or_degrade(
            "You are a listing copywriter. You may only rephrase facts already given -- never invent new facts, "
            "numbers, or claims.",
            prompt, _TitleRewrite,
            agent="listing_intelligence", product_name=product["name"],
        )

    if not result["available"]:
        return {"provenance": "LIVE", "product_id": product_id, "proposed": None, **{k: result[k] for k in ("message", "error", "provider", "model")}}

    proposed_title = result["data"]["proposed_title"]
    grounding = check_rewrite_grounding(original_fields, proposed_title)
    if not grounding["grounded"]:
        log_decision(agent="listing_intelligence", product_name=product["name"], action="grounding_strip",
                     detail={"field": "title", "reason": grounding["reason"]})
        return {
            "provenance": "LIVE", "product_id": product_id, "proposed": None,
            "message": "The AI proposal introduced unsupported facts and was rejected before being shown.",
            "grounding": grounding,
        }

    rec_id = idb.insert_listing_recommendation(
        product_id, None, "title", listing["title"], proposed_title, result["data"]["changes"],
        datetime.now(timezone.utc).isoformat(),
    )
    return {
        "provenance": "LIVE", "product_id": product_id, "recommendation_id": rec_id,
        "current_title": listing["title"], "proposed_title": proposed_title,
        "changes": result["data"]["changes"], "grounding": grounding,
    }


@router.post("/listing-intelligence/{product_id}/approve")
def approve_listing(product_id: str, body: IntelligenceApproveRequest) -> dict:
    product = get_product_or_404(product_id)
    action = f"decision_{body.decision}"
    if body.field and body.field.isdigit():
        idb.update_listing_recommendation_status(int(body.field), body.decision)
    log_decision(agent="human", product_name=product["name"], action=action,
                 detail={"module": "listing", "field": body.field, "reason": body.reason, "decided_by": body.decided_by})
    return {"recorded": True, "action": action}


@router.get("/listing-intelligence/{product_id}/history")
def listing_history(product_id: str) -> dict:
    get_product_or_404(product_id)
    return {
        "runs": [dict(r) for r in idb.get_intelligence_runs(module="listing", product_id=product_id)],
        "audits": [dict(r) for r in idb.get_listing_audit_history(product_id)],
        "recommendations": [dict(r) for r in idb.get_listing_recommendations(product_id)],
    }
