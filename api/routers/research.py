from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api import deps  # noqa: F401
from api.schemas import ResearchRequest

from cache_store import get_cached_bundle
from research_agent import CACHE_TTL_HOURS, run_research_agent

router = APIRouter(tags=["research"])


@router.post("/research")
def do_research(body: ResearchRequest) -> dict:
    """Agent 5 only — raw findings, no conclusions. Determines
    LIVE-vs-CACHE-HIT by checking the cache ourselves before calling
    run_research_agent (read-only introspection, not new agent logic),
    using the SAME ttl the agent itself uses so the two can never
    silently disagree about what counts as fresh."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")

    cache_hit = False
    cache_age_seconds = None

    if body.use_cache:
        cached = get_cached_bundle(body.product_name, ttl_hours=CACHE_TTL_HOURS)
        if cached is not None:
            cache_hit = True
            try:
                gathered_at = datetime.fromisoformat(cached.gathered_at)
                cache_age_seconds = (datetime.now(timezone.utc) - gathered_at).total_seconds()
            except (ValueError, TypeError):
                cache_age_seconds = None

    try:
        bundle = run_research_agent(body.product_name, use_cache=body.use_cache)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Research agent failed: {exc}") from exc

    return {
        "bundle": bundle.model_dump(),
        "cache_hit": cache_hit,
        "cache_age_seconds": cache_age_seconds,
    }
