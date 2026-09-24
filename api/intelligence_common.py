"""
intelligence_common.py — shared helpers for the four intelligence-module
routers: product lookup, intelligence_runs tracking (the shared
observability table), and the "ask the LLM, degrade gracefully" pattern
every module's optional explanation step uses. Deterministic analysis
never depends on any of this succeeding.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from api import deps  # noqa: F401

import db
import intelligence_db as idb
from decision_log import log_decision
from providers.llm import get_llm_provider


def get_product_or_404(product_id: str) -> dict:
    products = {p["product_id"]: p for p in db.get_products()}
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    return dict(products[product_id])


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunTracker:
    """Records one intelligence_runs row spanning the `with` block.
    provenance defaults to SYNTHETIC (pure deterministic engines); pass
    provenance="LIVE" for a block that also calls a real LLM/web provider."""

    def __init__(self, product_id: str, module: str, provenance: str = "SYNTHETIC") -> None:
        self.product_id = product_id
        self.module = module
        self.provenance = provenance
        self.run_id = str(uuid.uuid4())

    def __enter__(self) -> "RunTracker":
        idb.start_intelligence_run(self.run_id, self.product_id, self.module, self.provenance, now_iso())
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        idb.complete_intelligence_run(self.run_id, "failed" if exc_type else "complete", now_iso())
        return False  # never swallow the exception


def explain_or_degrade(
    system: str, prompt: str, schema: type[BaseModel], *, agent: str, product_name: str,
) -> dict[str, Any]:
    """Never raises. On any provider failure/unavailability, returns a
    well-formed "unavailable" result instead — the deterministic analysis
    around this call must always still work.

    Every call logs one "llm_request" decision-trace entry (spec §48's
    "LLM invocation count") through the same centralized decision_log —
    no second metrics mechanism."""
    provider = get_llm_provider()
    result = provider.explain(system, prompt, schema)
    log_decision(
        agent=agent, product_name=product_name, action="llm_request",
        detail={"provider": result.provider, "model": result.model, "available": result.available,
                "error": None if result.available else result.error},
    )
    if not result.available:
        return {
            "available": False,
            "provider": result.provider,
            "model": result.model,
            "message": "AI explanation unavailable; deterministic analysis available.",
            "error": result.error,
            "data": None,
        }
    return {
        "available": True,
        "provider": result.provider,
        "model": result.model,
        "message": None,
        "error": None,
        "data": result.data.model_dump(),
    }
