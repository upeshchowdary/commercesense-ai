from __future__ import annotations

from fastapi import APIRouter

from api import deps  # noqa: F401

from decision_log import read_decisions

router = APIRouter(tags=["agents"])

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
]


@router.get("/agents")
def list_agents() -> list[dict]:
    # One read of the whole log, not one read per agent per
    # log_agent_name (6 reads of the same file for 4 agent cards).
    all_entries = read_decisions()

    result = []
    for meta in _AGENT_META:
        names = set(meta["log_agent_names"])
        last = next((e for e in all_entries if e.get("agent") in names), None)
        result.append(
            {
                **{k: v for k, v in meta.items() if k != "log_agent_names"},
                "last_action": last["action"] if last else None,
                "last_product": last["product_name"] if last else None,
                "last_executed_at": last["timestamp"] if last else None,
                "status": "idle" if last else "never_run",
            }
        )
    return result
