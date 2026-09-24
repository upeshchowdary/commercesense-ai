from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from api import deps  # noqa: F401
from api.intelligence_common import RunTracker, explain_or_degrade, get_product_or_404
from api.schemas import IntelligenceApproveRequest, ReviewRefreshRequest

import db
import intelligence_db as idb
from decision_log import log_decision
from review_engine import (
    detect_emerging_issues,
    discover_candidate_words,
    rating_stats,
    review_velocity,
    semantic_theme_clusters,
    theme_frequency,
    themes_for_category,
)

router = APIRouter(tags=["review-intelligence"])


class _ReviewSummary(BaseModel):
    sentiment_summary: str
    suggested_investigation: str
    confidence: Literal["none", "low", "medium", "high"]


def _category_for(product_id: str) -> str:
    products = {p["product_id"]: p for p in db.get_products()}
    return products[product_id]["category"]


def _analyze(product_id: str, window_days: int = 30) -> dict:
    category = _category_for(product_id)
    reviews = [dict(r) for r in idb.get_review_items(product_id)]

    stats = rating_stats(reviews)
    velocity = review_velocity(reviews, window_days=window_days)

    candidate_themes = list(dict.fromkeys(themes_for_category(category) + discover_candidate_words(reviews, top_n=6)))
    themes = theme_frequency(reviews, candidate_themes)

    emerging = []
    for theme in candidate_themes:
        result = detect_emerging_issues(reviews, theme, window_days=window_days)
        if result:
            emerging.append(result)

    # Optional local-semantic lens (spec 10.4) alongside the deterministic
    # keyword/phrase themes above -- [] when sentence-transformers/
    # scikit-learn aren't installed, never a hard failure.
    semantic_clusters = semantic_theme_clusters(reviews)

    return {
        "product_id": product_id,
        "category": category,
        "rating_stats": stats,
        "velocity": velocity,
        "themes": themes[:8],
        "semantic_themes": semantic_clusters,
        "semantic_themes_available": len(semantic_clusters) > 0,
        "emerging_issues": emerging,
        "total_reviews_available": len(reviews),
    }


@router.get("/review-intelligence/{product_id}")
def get_review_intelligence(product_id: str) -> dict:
    get_product_or_404(product_id)
    return {"provenance": "SYNTHETIC", **_analyze(product_id)}


@router.post("/review-intelligence/{product_id}/analyze")
def analyze_reviews(product_id: str) -> dict:
    product = get_product_or_404(product_id)
    with RunTracker(product_id, "review", "SYNTHETIC"):
        analysis = _analyze(product_id)

    top_themes = ", ".join(f"{t['theme']} ({t['mentions']} mentions, {t['negative']} negative)" for t in analysis["themes"][:5]) or "none detected"
    emerging_text = "; ".join(e["explanation"] for e in analysis["emerging_issues"]) or "none detected"
    prompt = (
        f"Average rating: {analysis['rating_stats']['avg_rating']} across {analysis['rating_stats']['total_reviews']} reviews. "
        f"Negative %: {analysis['rating_stats']['negative_pct']}. Review velocity trend: {analysis['velocity']['trend']}. "
        f"Top themes: {top_themes}. Emerging issues: {emerging_text}. "
        "Summarize overall customer sentiment in 1-2 sentences and suggest one thing worth investigating. "
        "Only use the statistics and themes given -- never invent a complaint that wasn't listed."
    )
    explanation = explain_or_degrade(
        "You are a customer feedback analyst. Only summarize the verified statistics and themes given.",
        prompt, _ReviewSummary,
    )

    idb.insert_review_analysis(
        product_id, 30, analysis["rating_stats"]["total_reviews"] or 0, analysis["rating_stats"]["avg_rating"] or 0,
        analysis["rating_stats"]["rating_distribution"], analysis["rating_stats"]["negative_pct"] or 0,
        analysis["velocity"]["current_count"], analysis["velocity"]["previous_count"], analysis["velocity"]["trend"],
        analysis["themes"], analysis["emerging_issues"], datetime.now(timezone.utc).isoformat(),
    )
    log_decision(agent="review_intelligence", product_name=product["name"], action="analyzed",
                 detail={"avg_rating": analysis["rating_stats"]["avg_rating"], "emerging_issue_count": len(analysis["emerging_issues"])})
    return {"provenance": "SYNTHETIC", **analysis, "ai_summary": explanation}


@router.get("/review-intelligence/{product_id}/themes")
def get_themes(product_id: str) -> dict:
    get_product_or_404(product_id)
    analysis = _analyze(product_id)
    return {"provenance": "SYNTHETIC", "product_id": product_id, "themes": analysis["themes"]}


@router.get("/review-intelligence/{product_id}/trend")
def get_trend(product_id: str) -> dict:
    get_product_or_404(product_id)
    reviews = [dict(r) for r in idb.get_review_items(product_id)]
    return {
        "provenance": "SYNTHETIC", "product_id": product_id,
        "windows": {str(w): review_velocity(reviews, window_days=w) for w in (7, 30, 90)},
    }


@router.post("/review-intelligence/{product_id}/refresh")
def refresh(product_id: str, body: ReviewRefreshRequest) -> dict:
    get_product_or_404(product_id)
    with RunTracker(product_id, "review", "SYNTHETIC"):
        analysis = _analyze(product_id, window_days=body.window_days)
    return {"provenance": "SYNTHETIC", **analysis}


@router.post("/review-intelligence/{product_id}/approve")
def approve_review(product_id: str, body: IntelligenceApproveRequest) -> dict:
    product = get_product_or_404(product_id)
    action = f"decision_{body.decision}"
    log_decision(agent="human", product_name=product["name"], action=action,
                 detail={"module": "review", "field": body.field, "reason": body.reason, "decided_by": body.decided_by})
    return {"recorded": True, "action": action}
