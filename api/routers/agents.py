from __future__ import annotations

from fastapi import APIRouter

from api import deps  # noqa: F401

import intelligence_db as idb
from decision_log import read_decisions

router = APIRouter(tags=["agents"])

# Maps an agent id to the module string used as intelligence_runs.module
# (see RunTracker call sites in api/routers/{listing,pricing,review,
# inventory}_intelligence.py) -- only the four intelligence agents have
# run-tracked observability; the original Phase 1-3 agents predate that
# table and are covered by their own decision-log trace instead.
_RUN_TRACKED_MODULE: dict[str, str] = {
    "listing_intelligence": "listing",
    "pricing_intelligence": "pricing",
    "review_intelligence": "review",
    "inventory_intelligence": "inventory",
}

_AGENT_META = [
    {
        "id": "research_agent",
        "name": "Research Agent",
        "technology": "Gemini + Tavily",
        "purpose": "Collects and structures external research. Draws no conclusions.",
        "kind": "live",
        "log_agent_names": ["research_agent"],
    },
    {
        "id": "insight_agent",
        "name": "Insight Agent",
        "technology": "Gemini (structured output)",
        "purpose": "Generates grounded insights from research evidence.",
        "kind": "live",
        "mode": "Grounding-Enforced",
        "log_agent_names": ["insight_agent"],
    },
    {
        "id": "signal_detector",
        "name": "Signal Detector",
        "technology": "Deterministic rules (no LLM)",
        "purpose": "Identifies meaningful business signals from synthetic seller data.",
        "kind": "synthetic",
        "log_agent_names": ["inventory_signal", "ppc_waste_signal", "rank_bb_signal"],
    },
    {
        "id": "orchestrator",
        "name": "Orchestrator",
        "technology": "Python",
        "purpose": "Coordinates the research -> insight pipeline.",
        "kind": "live",
        "log_agent_names": ["orchestrator"],
    },
    {
        "id": "listing_intelligence",
        "name": "Listing Intelligence Agent",
        "technology": "Deterministic rules + optional LLM (Ollama/Gemini)",
        "purpose": "Scores listing completeness/quality and proposes grounded rewrites.",
        "kind": "synthetic",
        "mode": "Grounding-Enforced",
        "log_agent_names": ["listing_intelligence"],
    },
    {
        "id": "pricing_intelligence",
        "name": "Pricing Intelligence Agent",
        "technology": "Deterministic financial math + optional LLM",
        "purpose": "Computes margin, breakeven, and a justified price range.",
        "kind": "synthetic",
        "log_agent_names": ["pricing_intelligence"],
    },
    {
        "id": "review_intelligence",
        "name": "Review Intelligence Agent",
        "technology": "Deterministic statistics/theme frequency + optional LLM",
        "purpose": "Surfaces rating trends, complaint themes, and emerging issues.",
        "kind": "synthetic",
        "log_agent_names": ["review_intelligence"],
    },
    {
        "id": "inventory_intelligence",
        "name": "Inventory Intelligence Agent",
        "technology": "Deterministic demand/forecast math + optional LLM",
        "purpose": "Computes days of cover, reorder point, and reorder quantity.",
        "kind": "synthetic",
        "log_agent_names": ["inventory_intelligence"],
    },
]


@router.get("/agents")
def list_agents() -> list[dict]:
    # One read of the whole log, not one read per agent per
    # log_agent_name (6 reads of the same file for 4 agent cards).
    all_entries = read_decisions()

    result = []
    for meta in _AGENT_META:
        names = set(meta["log_agent_names"])
        agent_entries = [e for e in all_entries if e.get("agent") in names]
        last = agent_entries[0] if agent_entries else None

        llm_entries = [e for e in agent_entries if e.get("action") == "llm_request"]
        llm_available = sum(1 for e in llm_entries if e.get("detail", {}).get("available"))

        card = {
            **{k: v for k, v in meta.items() if k != "log_agent_names"},
            "last_action": last["action"] if last else None,
            "last_product": last["product_name"] if last else None,
            "last_executed_at": last["timestamp"] if last else None,
            "status": "idle" if last else "never_run",
            # spec §48 observability counters -- all derived live from the
            # existing decision log / intelligence_runs table, never a
            # second tracking mechanism and never fabricated.
            "llm_invocation_count": len(llm_entries),
            "llm_available_count": llm_available,
        }

        module = _RUN_TRACKED_MODULE.get(meta["id"])
        if module:
            card["run_stats"] = idb.get_intelligence_run_stats(module)

        result.append(card)
    return result
