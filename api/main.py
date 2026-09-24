"""
main.py — FastAPI entry point. Run with:
    uvicorn api.main:app --reload --port 8000
from the project root (so `api` resolves as a package and `deps.py`'s
project-root-relative sys.path setup lands in the right place).
"""

from __future__ import annotations

import os

from api import deps  # noqa: F401  (sys.path side effect — must run first)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    agents,
    data_import,
    decisions,
    evaluation,
    intelligence,
    inventory_intelligence,
    listing_intelligence,
    opportunity,
    pricing_intelligence,
    products,
    research,
    review_intelligence,
    signals,
)

app = FastAPI(title="Amazon Seller Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _flag(name: str, default: str = "true") -> bool:
    """Spec §57 feature flags. Each of the four intelligence modules can
    be switched off entirely by unsetting its router -- not just hidden
    in the UI -- so ENABLE_X_INTELLIGENCE=false genuinely disables that
    module's API surface (404s) rather than being decorative."""
    return os.environ.get(name, default).lower() == "true"


FEATURE_FLAGS = {
    "listing_intelligence": _flag("ENABLE_LISTING_INTELLIGENCE"),
    "pricing_intelligence": _flag("ENABLE_PRICING_INTELLIGENCE"),
    "review_intelligence": _flag("ENABLE_REVIEW_INTELLIGENCE"),
    "inventory_intelligence": _flag("ENABLE_INVENTORY_INTELLIGENCE"),
    "sp_api": _flag("ENABLE_SP_API", "false"),
    "searxng": _flag("ENABLE_SEARXNG", "false"),
    "ollama": _flag("ENABLE_OLLAMA", "true"),
}

app.include_router(products.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
if FEATURE_FLAGS["inventory_intelligence"]:
    app.include_router(inventory_intelligence.router, prefix="/api")
if FEATURE_FLAGS["listing_intelligence"]:
    app.include_router(listing_intelligence.router, prefix="/api")
if FEATURE_FLAGS["pricing_intelligence"]:
    app.include_router(pricing_intelligence.router, prefix="/api")
if FEATURE_FLAGS["review_intelligence"]:
    app.include_router(review_intelligence.router, prefix="/api")
app.include_router(opportunity.router, prefix="/api")
app.include_router(data_import.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    """Never exposes secret values — booleans only (spec §32, standing
    rule 1)."""
    return {
        "status": "ok",
        "gemini_api_key_set": bool(os.environ.get("GEMINI_API_KEY")),
        "tavily_api_key_set": bool(os.environ.get("TAVILY_API_KEY")),
        "llm_provider": os.environ.get("LLM_PROVIDER", "ollama"),
        "feature_flags": FEATURE_FLAGS,
    }
