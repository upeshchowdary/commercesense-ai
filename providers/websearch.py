"""
websearch.py — the one place Pricing Intelligence (the only module that
needs live web research, for competitor price observations) reaches for
live search. This deliberately does NOT build a second research engine: it
calls the exact same agent/research_agent.py used by the existing
Research/Insight agents (Tavily + Gemini query planning, the project's
cache, the project's decision log) and simply hands the raw findings back
for the pricing engine to extract price mentions from itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("agent",):
    _p = str(_PROJECT_ROOT / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from research_agent import run_research_agent  # noqa: E402
from schema import ResearchBundle  # noqa: E402


def research_competitor_prices(product_name: str, use_cache: bool = True) -> ResearchBundle:
    query_subject = f"{product_name} price comparison competitor pricing"
    return run_research_agent(query_subject, use_cache=use_cache)
