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
