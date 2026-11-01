"""
websearch.py — the WebSearchProvider abstraction with Free-First Hard Gate.

In CommerceSense AI v3 with FREE_ONLY=true:
  - Paid Tavily search is blocked by the hard gate.
  - Free self-hosted SearXNG is supported if enabled and configured.
  - If unconfigured, degrades safely to NoOpWebSearchProvider (returning empty findings)
    without raising unexpected network errors.
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

from schema import ResearchBundle, SearchFinding  # noqa: E402
from providers.gate import (  # noqa: E402
    FreeFirstPolicyViolationError,
    is_free_only_mode,
    validate_egress_url,
    validate_provider_initialization,
)


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


class NoOpWebSearchProvider:
    """Safe fallback when no free web search provider is configured."""
    name = "noop"

    def is_configured(self) -> bool:
        return False

    def search(self, query: str, max_results: int = 5, recency_days: int | None = None) -> list[dict]:
        return []


class TavilyProvider:
    """Paid Tavily provider. Blocked under FREE_ONLY=true."""
    name = "tavily"

    def __init__(self) -> None:
        validate_provider_initialization(self.name)

    def is_configured(self) -> bool:
        if is_free_only_mode():
            return False
        return bool(os.environ.get("TAVILY_API_KEY"))

    def search(self, query: str, max_results: int = 5, recency_days: int | None = None) -> list[dict]:
        if is_free_only_mode():
            raise FreeFirstPolicyViolationError("Tavily is blocked under FREE_ONLY=true policy")
        from research_agent import run_research_agent
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
    """Free SearXNG JSON API client."""
    name = "searxng"

    def __init__(self) -> None:
        self.base_url = os.environ.get("SEARXNG_URL", "").rstrip("/")
        if self.base_url:
            validate_egress_url(self.base_url)

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def search(self, query: str, max_results: int = 5, recency_days: int | None = None) -> list[dict]:
        if not self.is_configured():
            return []
        params = {"q": query, "format": "json"}
        if recency_days is not None:
            params["time_range"] = "day" if recency_days <= 1 else "week" if recency_days <= 7 else "month"
        url = f"{self.base_url}/search?{urllib_parse.urlencode(params)}"
        try:
            req = urllib_request.Request(url, headers={"Accept": "application/json"})
            with urllib_request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
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

    if is_free_only_mode():
        return NoOpWebSearchProvider()

    return TavilyProvider()


def research_competitor_prices(product_name: str, use_cache: bool = True) -> ResearchBundle:
    """Used by pricing_intelligence.py for competitor price observations."""
    query_subject = f"{product_name} price comparison competitor pricing"
    provider = get_websearch_provider()

    if isinstance(provider, TavilyProvider):
        from research_agent import run_research_agent
        return run_research_agent(query_subject, use_cache=use_cache)

    results = provider.search(query_subject, max_results=8)
    now = datetime.now(timezone.utc).isoformat()
    return ResearchBundle(
        product_name=product_name,
        findings=[
            SearchFinding(query=query_subject, source_url=r["url"], snippet=r["snippet"], retrieved_at=now)
            for r in results
        ],
        search_queries_used=[query_subject] if results else [],
        gathered_at=now,
    )
