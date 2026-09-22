"""
research_agent.py  Agent 5: Market Intelligence Agent (LIVE)

Given a product name, this agent decides what's worth searching for on
the live web, calls a single scoped web_search tool (backed by Tavily,
falling back to DuckDuckGo if no Tavily key is set), and returns a
structured, UNINTERPRETED bundle of findings. It draws no conclusions 
that is Agent 6's job (insight_agent.py, Phase 2).

CUBE alignment:
  - Tools: exactly one tool (web_search), scoped, hard-capped.
  - Context: every finding keeps its source_url + retrieved_at.
  - Decision tracing: every run appends an entry to decisions.log.jsonl.
  - Accountability: this is the only part of the project that spends
    real, metered quota  it must never run automatically, only on
    demand (enforced by the caller in later phases, not here).

Uses Gemini's automatic function calling, forced via tool_config
mode="ANY". The default AUTO mode lets the model decide not to call
any tool at all  observed in testing, where the model sometimes
answered from training-data recall instead of searching. ANY mode
forces a function call on every turn instead of leaving that
decision to the model. automatic_function_calling.maximum_remote_calls
is capped to exactly MAX_SEARCHES so every forced round-trip is a
genuine search, not a wasted extra call after the budget is spent.

A minimal fallback (exactly one search, using the product name itself)
covers the residual edge case where zero tool calls still happen
somehow  logged explicitly, never silent.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from google import genai
from google.genai import types

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
MAX_SEARCHES = 4  # hard cap  enforced in code, not just in the prompt
CACHE_TTL_HOURS = 6

SYSTEM_PROMPT = """You are a market research agent for an Amazon seller's \
assistant tool. You are given one product. Your only job is to decide \
what to search for and call the web_search tool to gather RAW \
information about that product from the live web: news, pricing \
mentions, competitor products, trends, known issues or complaints.

Rules:
- You have at most {max_searches} searches available. Spend them on \
  distinct angles  for example: current pricing, recent news, \
  competitor products, known issues/complaints. Do not repeat a \
  near-identical query.
- Do NOT draw conclusions, do NOT summarize, do NOT decide what \
  matters. A separate agent handles that. Your only job is to gather.
- Even if you believe you already know about this product, you must \
  still search  your own prior knowledge may be outdated, and this \
  tool's entire purpose is finding what's true right now.
"""


class _SearchCollector:
    """Accumulates real search results across however many times
    Gemini's automatic function calling invokes web_search during one
    generate_content call."""

    def __init__(self, max_searches: int) -> None:
        self.max_searches = max_searches
        self.calls_made = 0
        self.findings: list[SearchFinding] = []
        self.queries_used: list[str] = []


def _execute_search(query: str) -> list[dict]:
    """Runs the actual search against Tavily, or DuckDuckGo if no
    Tavily key is configured. Returns a list of {url, content} dicts."""
    if _tavily is not None:
        try:
            result = _tavily.search(query, max_results=4)
            return [
                {"url": r.get("url", ""), "content": r.get("content", "")[:800]}
                for r in result.get("results", [])
            ]
        except Exception as exc:  # noqa: BLE001  surface, don't crash the run
            return [{"url": "", "content": f"[search error: {exc}]"}]

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=4))
        return [
            {"url": h.get("href", ""), "content": h.get("body", "")[:800]}
            for h in hits
        ]
    except Exception as exc:  # noqa: BLE001
        return [{"url": "", "content": f"[no search backend available: {exc}]"}]


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
    collector = _SearchCollector(MAX_SEARCHES)

    def web_search(query: str) -> str:
        """Search the live web for real-time information about a product.

        Use this to find news, pricing mentions, competitor products, or
        trend/complaint signals. Each call costs quota, so make queries
        specific and avoid repeating the same angle twice.

        Args:
            query: A specific, non-redundant search query.
        """
        if collector.calls_made >= collector.max_searches:
            return json.dumps(
                {"error": "search budget exhausted  stop calling this tool"}
            )

        collector.calls_made += 1
        collector.queries_used.append(query)
        results = _execute_search(query)

        for r in results:
            collector.findings.append(
                SearchFinding(
                    query=query,
                    source_url=r["url"],
                    snippet=r["content"],
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        return json.dumps({"query": query, "results": results})

    client.models.generate_content(
        model=MODEL,
        contents=f"Gather live web information about this product: {product_name!r}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT.format(max_searches=MAX_SEARCHES),
            tools=[web_search],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY")
            ),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=MAX_SEARCHES
            ),
        ),
    )
    # Automatic function calling has already run the full loop by the
    # time generate_content returns  collector is fully populated,
    # UNLESS the fallback below had to fire.

    if collector.calls_made == 0:
        # Forcing mode="ANY" should make this unreachable. If it still
        # happens, don't return an empty bundle silently  log it
        # clearly and do exactly one search so downstream agents still
        # get something real to work with.
        log_decision(
            agent="research_agent",
            product_name=product_name,
            action="zero_tool_calls_fallback",
            detail={"reason": "Gemini made no tool calls despite mode=ANY"},
        )
        fallback_results = _execute_search(product_name)
        collector.queries_used.append(product_name)
        collector.calls_made += 1
        for r in fallback_results:
            collector.findings.append(
                SearchFinding(
                    query=product_name,
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
