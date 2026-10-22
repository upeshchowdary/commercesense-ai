"""
keyless_search.py — optional, no-API-key web search fallback for the
Research Agent, using the open-source `ddgs` metasearch library (MIT).

OFF by default. Turn on with ENABLE_KEYLESS_SEARCH=true. It is only ever
used when Tavily is missing or returned nothing, so Tavily stays the
primary backend and a seller with a Tavily key sees no change.

Honest limits, so nobody over-trusts it:
  - ddgs queries public search engines without an official API contract,
    so results can be rate-limited, blocked or change shape without
    notice. A failure is logged and yields NO findings -- never a fake one.
  - It was not run against the live web in the build environment (no
    outbound access to search engines there); the parsing is covered by
    mocked tests only. Run one real query before a demo.
  - Every result keeps its real URL and snippet, so Agent 6's existing
    grounding guardrails (non-empty snippet, snippet must appear in the
    findings) apply to these results exactly as they do to Tavily's.
"""

from __future__ import annotations

import os
from typing import Callable

from decision_log import log_decision


def is_enabled() -> bool:
    return os.environ.get("ENABLE_KEYLESS_SEARCH", "false").lower() == "true"


def _default_backend(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS  # imported lazily: optional dependency

    return list(DDGS().text(query, max_results=max_results))


def keyless_search(
    query: str,
    product_name: str,
    max_results: int = 4,
    *,
    backend: Callable[[str, int], list[dict]] | None = None,
    truncate: Callable[[str, int], str] | None = None,
) -> list[dict]:
    """Returns [{"url", "content"}] in the same shape research_agent's
    Tavily path produces. `backend` and `truncate` are injectable so the
    parsing can be tested without network access."""
    try:
        raw = (backend or _default_backend)(query, max_results)
    except ImportError:
        log_decision(
            agent="research_agent", product_name=product_name, action="search_backend_missing",
            detail={"query": query, "reason": "ENABLE_KEYLESS_SEARCH is on but the 'ddgs' package is not installed"},
        )
        return []
    except Exception as exc:  # noqa: BLE001 -- a search failure must never crash the agent
        log_decision(
            agent="research_agent", product_name=product_name, action="search_failed",
            detail={"query": query, "backend": "ddgs", "reason": str(exc)},
        )
        return []

    cut = truncate or (lambda text, n: text[:n])
    results = []
    for r in raw:
        url = (r.get("href") or r.get("url") or "").strip()
        body = (r.get("body") or r.get("snippet") or "").strip()
        # A result with no URL or no text cannot be cited, so it is dropped
        # here rather than passed on as a finding.
        if url and body:
            results.append({"url": url, "content": cut(body, 800)})

    log_decision(
        agent="research_agent", product_name=product_name, action="search_fallback_used",
        detail={"query": query, "backend": "ddgs", "results": len(results)},
    )
    return results
