"""
websearch.py — the WebSearchProvider abstraction (spec §22). The rest of
the app never talks to a specific search backend directly; it calls
research_competitor_prices() below, which picks a provider and always
hands back the same ResearchBundle shape regardless of which one ran.

Two providers:
  - TavilyProvider (default): does NOT build a second research engine --
    it calls the exact same agent/research_agent.py used by the existing
    Research/Insight agents (Tavily + Gemini query planning, the
    project's cache, the project's decision log) and hands the raw
    findings back for the pricing engine to extract price mentions from.
  - SearXNGProvider (optional, off by default): a real HTTP client
    against a self-hosted SearXNG instance's JSON API
    (GET {url}/search?q=...&format=json). Only used when both
    ENABLE_SEARXNG=true and SEARXNG_URL are set; nothing in this project
    stands up a SearXNG instance, so this is a genuine implementation
    that is simply unconfigured/unused until someone points it at a real
    one. Falls back to TavilyProvider automatically if unconfigured.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import URLError

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("agent",):
    _p = str(_PROJECT_ROOT / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from research_agent import run_research_agent  # noqa: E402
from schema import ResearchBundle, SearchFinding  # noqa: E402


class SearchResult(Protocol):
    title: str
    url: str
    snippet: str
    published_at: str | None
    source: str


class WebSearchProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def search(self, query: str, max_results: int = 5, recency_days: int | None = None) -> list[dict]: ...


class TavilyProvider:
    """Wraps the existing Research Agent pipeline (Tavily + Gemini query
    planning, project cache, project decision log) rather than a second
    engine. is_configured() mirrors the same TAVILY_API_KEY check
    research_agent.py itself makes."""

    name = "tavily"

    def is_configured(self) -> bool:
        return bool(os.environ.get("TAVILY_API_KEY"))

    def search(self, query: str, max_results: int = 5, recency_days: int | None = None) -> list[dict]:
        bundle = run_research_agent(query, use_cache=True)
        return [
            {
                "title": f.query,
                "url": f.source_url,
                "snippet": f.snippet,
                "published_at": None,
                "source": "tavily",
            }
            for f in bundle.findings[:max_results]
        ]


class SearXNGProvider:
    """Real SearXNG JSON API client. Unconfigured (is_configured() ==
    False) unless SEARXNG_URL is set -- callers must fall back to
    TavilyProvider rather than treat this as always-available."""

    name = "searxng"

    def __init__(self) -> None:
        self.base_url = os.environ.get("SEARXNG_URL", "").rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def search(self, query: str, max_results: int = 5, recency_days: int | None = None) -> list[dict]:
        if not self.is_configured():
            return []
        params = {"q": query, "format": "json"}
        if recency_days is not None:
            # SearXNG's coarse time_range buckets -- nearest fit, not exact.
            params["time_range"] = "day" if recency_days <= 1 else "week" if recency_days <= 7 else "month"
        url = f"{self.base_url}/search?{urllib_parse.urlencode(params)}"
        try:
            req = urllib_request.Request(url, headers={"Accept": "application/json"})
            with urllib_request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            return []
        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "published_at": item.get("publishedDate"),
                "source": "searxng",
            })
        return results


def get_websearch_provider() -> WebSearchProvider:
    if os.environ.get("ENABLE_SEARXNG", "false").lower() == "true":
        searxng = SearXNGProvider()
        if searxng.is_configured():
            return searxng
    return TavilyProvider()


def research_competitor_prices(product_name: str, use_cache: bool = True) -> ResearchBundle:
    """Used by pricing_intelligence.py for competitor price observations.
    Always returns a ResearchBundle regardless of which underlying
    provider ran, so callers never need to know which one was used."""
    query_subject = f"{product_name} price comparison competitor pricing"
    provider = get_websearch_provider()

    if isinstance(provider, TavilyProvider):
        # Preserves the exact existing cache/decision-log behavior.
        return run_research_agent(query_subject, use_cache=use_cache)

    results = provider.search(query_subject, max_results=8)
    now = datetime.now(timezone.utc).isoformat()
    return ResearchBundle(
        product_name=product_name,
        findings=[
            SearchFinding(query=query_subject, source_url=r["url"], snippet=r["snippet"], retrieved_at=now)
            for r in results
        ],
        search_queries_used=[query_subject],
        gathered_at=now,
    )
