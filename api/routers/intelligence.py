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
    from providers.gate import FreeFirstPolicyViolationError, is_free_only_mode

    if is_free_only_mode():
        raise HTTPException(
            status_code=403,
            detail="Live intelligence pipeline via Gemini/Tavily is blocked under FREE_ONLY policy. Use local intelligence modules or allow paid providers (ALLOW_PAID_PROVIDERS=true).",
        )

    try:
        bundle, report = run_market_intelligence_with_evidence(
            body.product_name, use_cache=body.use_cache
        )
    except FreeFirstPolicyViolationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Intelligence pipeline failed: {exc}") from exc

    return {
        "bundle": bundle.model_dump(),
        "report": report.model_dump(),
    }
