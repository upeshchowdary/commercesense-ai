"""
schema.py  the structured contract between Agent 5 (research) and
Agent 6 (insight). Nothing crosses this boundary informally: if it's
not in these models, it isn't part of the handoff.

This IS the A2A boundary from the CUBE deck, made concrete. Agent 5
only ever produces a ResearchBundle. Agent 6 only ever consumes one
and produces an InsightReport. Neither agent needs to know how the
other is implemented.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SearchFinding(BaseModel):
    """One raw result from one web search. Nothing interpreted yet."""

    query: str
    source_url: str
    snippet: str
    retrieved_at: str  # ISO-8601 timestamp


class ResearchBundle(BaseModel):
    """Raw output of Agent 5. Deliberately uninterpreted: no
    conclusions, no opinions, no 'this means...'. Just what was found,
    where it came from, and when."""

    product_name: str
    findings: list[SearchFinding] = Field(default_factory=list)
    search_queries_used: list[str] = Field(default_factory=list)
    gathered_at: str  # ISO-8601 timestamp


class Insight(BaseModel):
    """One conclusion drawn by Agent 6. Must be grounded in a specific
    finding, or explicitly marked as having none."""

    category: Literal["pricing", "trend", "risk", "opportunity"]
    summary: Optional[str] = None  # None means: no reliable data found
    confidence: Literal["none", "low", "medium", "high"] = "none"
    source_snippet: Optional[str] = None  # verbatim text this is based on
    source_url: Optional[str] = None

    def is_fabricated_risk(self) -> bool:
        """Cheap guardrail: a confident summary with no cited source is
        the exact shape of a hallucination that happens to be well
        formatted. Flag it so the caller can downgrade rather than
        trust it blindly."""
        return (
            self.summary is not None
            and self.confidence != "none"
            and not self.source_snippet
        )


class InsightReport(BaseModel):
    """Final output of Agent 6, and what the UI actually renders."""

    product_name: str
    insights: list[Insight]
    generated_at: str  # ISO-8601 timestamp
    grounded_count: int
    ungrounded_count: int
