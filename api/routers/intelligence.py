from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from api import deps  # noqa: F401
from api.schemas import IntelligenceRequest

from orchestrator import run_market_intelligence_with_evidence

router = APIRouter(tags=["intelligence"])


@router.post("/intelligence/run")
def run_intelligence(body: IntelligenceRequest) -> dict:
    """Calls agent/orchestrator.py's own pipeline function directly —
    no separate copy of the research->insight sequence here — so the
    two can never drift apart."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")

    try:
        bundle, report = run_market_intelligence_with_evidence(
            body.product_name, use_cache=body.use_cache
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Intelligence pipeline failed: {exc}") from exc

    return {
        "bundle": bundle.model_dump(),
        "report": report.model_dump(),
    }
