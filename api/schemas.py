"""Request bodies for the API layer. Agent/signal response shapes are
returned as plain dicts (via .model_dump() or sqlite3.Row -> dict) —
this file only covers what's genuinely new: what the frontend POSTs
in.

product_name is constrained (min length, trimmed) everywhere it feeds
a live agent call — an empty or whitespace-only name would otherwise
still trigger a real, metered Gemini + Tavily call for nothing."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class _ProductNameMixin(BaseModel):
    product_name: str = Field(min_length=2, max_length=200)

    @field_validator("product_name")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("product_name must be at least 2 non-whitespace characters")
        return v


class ResearchRequest(_ProductNameMixin):
    use_cache: bool = True


class IntelligenceRequest(_ProductNameMixin):
    use_cache: bool = True


class DecisionRequest(_ProductNameMixin):
    # the insight category or signal_type this decision concerns
    category: Literal[
        "pricing", "trend", "risk", "opportunity",
        "inventory_stockout", "ppc_waste", "rank_drop",
    ]
    decision: Literal["approved", "rejected", "more_research_requested"]
    reason: Optional[str] = None
    decided_by: Optional[str] = "Demo User"


# ---------------------------------------------------- Intelligence modules

class IntelligenceApproveRequest(BaseModel):
    """Shared shape for every module's /approve endpoint. Delegates to the
    exact same decision_log.py mechanism as /api/decisions — `field`
    identifies which specific recommendation this concerns (e.g. "title",
    "price_range", "reorder_quantity", "review_theme:warping")."""

    decision: Literal["approved", "rejected", "more_research_requested"]
    field: Optional[str] = None
    reason: Optional[str] = None
    decided_by: Optional[str] = "Demo User"


class ListingRewriteRequest(BaseModel):
    use_ai: bool = True


class PricingAnalyzeRequest(BaseModel):
    use_live_research: bool = False  # if true, calls the (reused) Research Agent for competitor prices


class PricingSimulateRequest(BaseModel):
    new_price: float = Field(gt=0, le=100000)
    ad_spend_levels: Optional[list[float]] = None


class InventorySimulateRequest(BaseModel):
    reorder_quantity: int = Field(ge=0, le=1_000_000)
    lead_time_days: Optional[int] = Field(default=None, ge=1, le=365)


class InboundShipment(BaseModel):
    day_offset: int = Field(ge=0, le=365)
    quantity: int = Field(ge=0, le=1_000_000)


class InventoryForecastRequest(BaseModel):
    days_ahead: int = Field(default=30, ge=1, le=180)
    inbound: list[InboundShipment] = Field(default_factory=list)


class ReviewRefreshRequest(BaseModel):
    window_days: int = Field(default=30, ge=7, le=90)
