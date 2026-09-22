"""
research_agent.py  Agent 5: Market Intelligence Agent (LIVE)

Given a product name, this agent plans up to MAX_SEARCHES distinct
search queries via Gemini structured output, executes them against
Tavily (or DuckDuckGo as a fallback), and returns a structured,
UNINTERPRETED bundle of findings. It draws no conclusions  that is
Agent 6's job (insight_agent.py, Phase 2).

DESIGN NOTE  why this doesn't use Gemini's automatic function calling:
Three independent attempts to get Gemini to reliably call a web_search
tool via automatic function calling (default AUTO mode, forced ANY
mode, and the SDK's own recommended Chat.send_message path) all
produced the same result: Gemini returned without ever invoking the
tool. This is a reproducible SDK/model-behavior issue, confirmed by
testing the same underlying mechanism three different ways across
three different products.

Instead, this agent uses a two-step, AFC-free design:
  1. PLAN  ask Gemini for a list of up to MAX_SEARCHES distinct
     search queries (with reasons), via response_schema structured
     output. No tools involved at all.
  2. EXECUTE  run that plan ourselves, in plain Python, calling
     Tavily/DDG directly for each planned query.

This keeps the model's judgment (deciding what's worth searching)
while removing the fragile automatic-calling machinery entirely.

CUBE alignment:
  - Tools: search execution is plain code, scoped and capped.
  - Context: every finding keeps its source_url + retrieved_at.
  - Decision tracing: the plan itself (queries + reasons) is logged,
    not just the outcome  "who decided what, on what evidence."
  - Accountability: this is the only part of the project that spends
    real, metered quota  it must never run automatically, only on
    demand (enforced by the caller in later phases, not here).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from google import genai
from google.genai import types
from pydantic import BaseModel

from schema import ResearchBundle, SearchFinding
from cache_store import get_cached_bundle, save_bundle_to_cache
from decision_log import log_decision

try:
    from tavily import TavilyClient

    _tavily = (
        TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        if os.environ.get("TAVILY_API_KEY")
        else None
    )
except ImportError:
    _tavily = None


MODEL = os.environ.get("RESEARCH_AGENT_MODEL", "gemini-2.5-flash")
MAX_SEARCHES = 4
CACHE_TTL_HOURS = 6

PLANNING_PROMPT = """You are a market research planner for an Amazon \
seller's assistant tool. You are given one product. Your only job is \
to plan up to {max_searches} distinct web search queries that would \
gather useful RAW information about it: current pricing, recent news, \
competitor products, and known issues or complaints.

Rules:
- Return at most {max_searches} queries. Fewer is fine if the product \
  is narrow, but cover distinct angles  do not return near-duplicate \
  queries.
- For each query, give a short one-phrase reason it's worth searching.
- Do NOT answer the questions yourself. Do NOT draw conclusions about \
  the product. Your only job is to plan what to search for.
"""


class _PlannedQuery(BaseModel):
    query: str
    reason: str


class _SearchCollector:
    """Accumulates real search results as planned queries are executed."""

    def __init__(self) -> None:
        self.findings: list[SearchFinding] = []
        self.queries_used: list[str] = []


def _truncate_at_word_boundary(text: str, max_chars: int) -> str:
    """Cut text down to at most max_chars WITHOUT slicing a word or a
    number in half  a hard character cutoff can chop a price or a
    sentence mid-way, which actively hurts Agent 6's ability to ground
    an insight in it later."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:  # don't lose too much just to land on a boundary
        truncated = truncated[:last_space]
    return truncated.rstrip() + ""


def _execute_search(query: str) -> list[dict]:
    """Runs the actual search against Tavily, or DuckDuckGo if no
    Tavily key is configured. Returns a list of {url, content} dicts."""
    if _tavily is not None:
        try:
            result = _tavily.search(query, max_results=4)
            return [
                {
                    "url": r.get("url", ""),
                    "content": _truncate_at_word_boundary(r.get("content", ""), 800),
                }
                for r in result.get("results", [])
            ]
        except Exception as exc:  # noqa: BLE001
            return [{"url": "", "content": f"[search error: {exc}]"}]

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=4))
        return [
            {
                "url": h.get("href", ""),
                "content": _truncate_at_word_boundary(h.get("body", ""), 800),
            }
            for h in hits
        ]
    except Exception as exc:  # noqa: BLE001
        return [{"url": "", "content": f"[no search backend available: {exc}]"}]


def _plan_queries(client: genai.Client, product_name: str) -> list[_PlannedQuery]:
    """Ask Gemini to plan up to MAX_SEARCHES distinct search queries,
    via structured output  no tools, no automatic function calling."""
    response = client.models.generate_content(
        model=MODEL,
        contents=f"Product: {product_name!r}",
        config=types.GenerateContentConfig(
            system_instruction=PLANNING_PROMPT.format(max_searches=MAX_SEARCHES),
            response_mime_type="application/json",
            response_schema=list[_PlannedQuery],
            max_output_tokens=512,
        ),
    )
    planned = response.parsed
    if not planned:
        raise ValueError("Gemini returned no query plan")
    queries = [
        item if isinstance(item, _PlannedQuery) else _PlannedQuery.model_validate(item)
        for item in planned
    ]
    return queries[:MAX_SEARCHES]  # defensive cap even though the prompt already asks for this


def _dedupe_queries(planned: list[_PlannedQuery]) -> list[_PlannedQuery]:
    """Defensive: the prompt asks Gemini for distinct angles, but never
    trust a prompt instruction alone to enforce that  the same lesson
    this project already learned the hard way with AFC. Drop literal
    duplicates (case/whitespace-insensitive) before they burn search
    quota on redundant queries."""
    seen: set[str] = set()
    deduped: list[_PlannedQuery] = []
    for pq in planned:
        key = " ".join(pq.query.strip().lower().split())
        if key not in seen:
            seen.add(key)
            deduped.append(pq)
    return deduped


def run_research_agent(product_name: str, use_cache: bool = True) -> ResearchBundle:
    """Gather live, structured findings about a product. Returns a
    ResearchBundle  never an opinion, never a conclusion."""

    if use_cache:
        cached = get_cached_bundle(product_name, ttl_hours=CACHE_TTL_HOURS)
        if cached is not None:
            log_decision(
                agent="research_agent",
                product_name=product_name,
                action="cache_hit",
                detail={"num_findings": len(cached.findings)},
            )
            return cached

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    collector = _SearchCollector()

    planned_queries: list[_PlannedQuery] | None = None
    last_error: Exception | None = None

    for attempt in range(2):  # one try, one retry  never give up after a single blip
        try:
            planned_queries = _plan_queries(client, product_name)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            log_decision(
                agent="research_agent",
                product_name=product_name,
                action="planning_attempt_failed",
                detail={"attempt": attempt + 1, "reason": str(exc)},
            )

    if planned_queries is None:
        # Both attempts failed  fall back honestly to the weakest
        # possible plan rather than crash. A known, logged degradation,
        # never a silent one.
        log_decision(
            agent="research_agent",
            product_name=product_name,
            action="planning_failed_fallback",
            detail={"reason": str(last_error)},
        )
        planned_queries = [
            _PlannedQuery(
                query=product_name,
                reason="planning failed twice, using product name directly",
            )
        ]
    else:
        planned_queries = _dedupe_queries(planned_queries)
        if len(planned_queries) < 2:
            # A schema-valid plan can still be a USELESS plan (e.g. all
            # near-duplicate queries collapsed to one). Never trust a
            # plan just because it parsed correctly  log this
            # explicitly so it's visible, not silently accepted.
            log_decision(
                agent="research_agent",
                product_name=product_name,
                action="degenerate_plan_warning",
                detail={"surviving_queries": len(planned_queries)},
            )
        log_decision(
            agent="research_agent",
            product_name=product_name,
            action="query_plan_created",
            detail={
                "queries": [
                    {"query": q.query, "reason": q.reason} for q in planned_queries
                ]
            },
        )

    for pq in planned_queries:
        results = _execute_search(pq.query)
        collector.queries_used.append(pq.query)
        for r in results:
            collector.findings.append(
                SearchFinding(
                    query=pq.query,
                    source_url=r["url"],
                    snippet=r["content"],
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                )
            )

    bundle = ResearchBundle(
        product_name=product_name,
        findings=collector.findings,
        search_queries_used=collector.queries_used,
        gathered_at=datetime.now(timezone.utc).isoformat(),
    )

    if use_cache:
        save_bundle_to_cache(bundle)

    log_decision(
        agent="research_agent",
        product_name=product_name,
        action="live_search",
        detail={
            "num_queries": len(collector.queries_used),
            "num_findings": len(collector.findings),
        },
    )

    return bundle


if __name__ == "__main__":
    import sys

    product = " ".join(sys.argv[1:]) or "Anker PowerCore 10000 portable charger"
    bundle = run_research_agent(product)
    print(json.dumps(bundle.model_dump(), indent=2))
