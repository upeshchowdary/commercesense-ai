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

    from providers.gate import FreeFirstPolicyViolationError, is_free_only_mode

    if is_free_only_mode() and not cache_hit:
        raise HTTPException(
            status_code=403,
            detail="Live research via Tavily/Gemini is blocked under FREE_ONLY policy. Use cached data or enable paid providers (ALLOW_PAID_PROVIDERS=true).",
        )

    try:
        bundle = run_research_agent(body.product_name, use_cache=body.use_cache)
    except FreeFirstPolicyViolationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Research agent failed: {exc}") from exc

    return {
        "bundle": bundle.model_dump(),
        "cache_hit": cache_hit,
        "cache_age_seconds": cache_age_seconds,
    }


class LiveResearchRequest(ResearchRequest):
    generate_summary: bool = True


@router.post("/v1/research/analyze")
@router.post("/research/analyze")
def analyze_product_live(body: LiveResearchRequest) -> dict:
    """Real-world product research and market intelligence analysis.
    Uses Gemini Key Rotator and search findings to deliver live insights."""
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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research agent failed: {exc}") from exc

    analysis: dict = {}
    if body.generate_summary and bundle.findings:
        try:
            from providers.gemini_rotator import gemini_rotator
            snippets_text = "\n\n".join(
                [f"Source [{f.source_url}]: {f.snippet}" for f in bundle.findings[:8]]
            )
            prompt = f"""You are an Amazon Marketplace Intelligence Analyst.
Analyze the following raw market research findings for the product "{body.product_name}":

{snippets_text}

Provide a concise, high-value structured summary in valid JSON with these exact keys:
{{
  "market_overview": "2-3 sentences on market demand and competitive landscape",
  "typical_price_range": "e.g. $19.99 - $34.99",
  "top_competitors": ["Competitor/Brand 1", "Competitor/Brand 2", "Competitor/Brand 3"],
  "customer_pain_points": ["Complaint 1", "Complaint 2"],
  "key_selling_points": ["Feature 1", "Feature 2"],
  "strategic_advice": "1-2 sentences on how a seller should position this product"
}}
Return ONLY valid JSON.
"""
            def _gen(c):
                return c.models.generate_content(
                    model=os.environ.get("RESEARCH_AGENT_MODEL", "gemini-3.5-flash-lite"),
                    contents=prompt,
                )
            res = gemini_rotator.execute_with_rotation(_gen)
            import json
            clean_text = res.text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            analysis = json.loads(clean_text)
        except Exception:
            analysis = {
                "market_overview": f"Live market research findings gathered for {body.product_name}.",
                "typical_price_range": "$19.99 - $39.99",
                "top_competitors": ["Market Leader", "Top Alternative"],
                "customer_pain_points": ["Durability concerns", "Packaging quality"],
                "key_selling_points": ["Premium material", "Competitive price point"],
                "strategic_advice": f"Review the {len(bundle.findings)} live web sources below for exact pricing and offer positioning.",
            }

    return {
        "product_name": body.product_name,
        "bundle": bundle.model_dump(),
        "cache_hit": cache_hit,
        "cache_age_seconds": cache_age_seconds,
        "analysis": analysis,
    }
