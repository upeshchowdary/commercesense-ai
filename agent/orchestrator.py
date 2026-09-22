"""
orchestrator.py — the one function the Streamlit app (Phase 5) or a
quick CLI run actually calls. This is the only file in the project
that imports both live agents; research_agent.py and insight_agent.py
never import each other directly. That boundary is the A2A design
decision from the CUBE deck made an enforced fact of the folder
structure, not just a comment — nothing else in this project is
allowed to import both agents itself.
"""

from __future__ import annotations

from research_agent import run_research_agent
from insight_agent import run_insight_agent
from schema import InsightReport
from decision_log import log_decision


def run_market_intelligence(product_name: str, use_cache: bool = True) -> InsightReport:
    """Full live pipeline: research -> insight.

    This is the function a "Refresh live intelligence" button in the
    UI (Phase 5) should call. It is never called automatically or on a
    schedule — only when a human asks for it, because every call here
    spends real, metered search + LLM quota.
    """
    log_decision(
        agent="orchestrator",
        product_name=product_name,
        action="pipeline_started",
        detail={"use_cache": use_cache},
    )

    bundle = run_research_agent(product_name, use_cache=use_cache)
    report = run_insight_agent(bundle)

    log_decision(
        agent="orchestrator",
        product_name=product_name,
        action="pipeline_completed",
        detail={
            "num_findings": len(bundle.findings),
            "grounded_count": report.grounded_count,
            "ungrounded_count": report.ungrounded_count,
        },
    )

    return report


if __name__ == "__main__":
    import json
    import sys

    product = " ".join(sys.argv[1:]) or "Anker PowerCore 10000 portable charger"
    report = run_market_intelligence(product)
    print(json.dumps(report.model_dump(), indent=2))
