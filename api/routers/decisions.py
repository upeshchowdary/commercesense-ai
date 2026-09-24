from __future__ import annotations

from fastapi import APIRouter, Query

from api import deps  # noqa: F401
from api.schemas import DecisionRequest

from decision_log import log_decision, read_decisions

router = APIRouter(tags=["decisions"])


@router.get("/activity")
def list_activity(
    product_name: str | None = Query(default=None),
    agent: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict]:
    return read_decisions(limit=limit, product_name=product_name, agent=agent, action=action)


@router.get("/activity/stats")
def activity_stats() -> dict:
    """Full-log aggregate counts (spec-driven fix: the Overview KPIs and
    charts were reading only the most recent 100 activity rows, which
    undercounts as soon as a bulk action -- e.g. running signal
    detection, which alone logs ~84 events -- pushes older rows out of
    that window). One read_decisions() pass over the entire log, not a
    second tracking mechanism."""
    entries = read_decisions()
    by_agent: dict[str, int] = {}
    by_action: dict[str, int] = {}
    for e in entries:
        by_agent[e.get("agent", "")] = by_agent.get(e.get("agent", ""), 0) + 1
        by_action[e.get("action", "")] = by_action.get(e.get("action", ""), 0) + 1
    return {"total": len(entries), "by_agent": by_agent, "by_action": by_action}


@router.post("/decisions")
def record_decision(body: DecisionRequest) -> dict:
    """The human-in-the-loop record (spec §17-18). No such concept
    exists elsewhere in the codebase — added the same way everything
    else is added: through decision_log.py, never a second mechanism."""
    action = f"decision_{body.decision}"
    log_decision(
        agent="human",
        product_name=body.product_name,
        action=action,
        detail={
            "category": body.category,
            "reason": body.reason,
            "decided_by": body.decided_by,
        },
    )
    return {"recorded": True, "action": action}
