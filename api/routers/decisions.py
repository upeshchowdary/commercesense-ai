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
