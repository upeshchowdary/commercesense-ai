"""
actions.py — Action Center & Automation Management Router for CommerceSense AI v3.

Provides endpoints for:
1. Approval Inbox: Reviewing drafted actions (QUEUED, APPROVED, REJECTED, SNOOZED).
2. Action Decisions: Human-in-the-loop decisions with itemized "Why Panel" audit trails.
3. Automation Rules: CRUD and execution triggers for catalog-wide rule evaluation.
4. Audit Log: Immutable event history of all operational decisions and actions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from api import deps
from db.models import ActionQueueItem, AutomationRule, AuditEvent, Product
from db.session import get_db
from decision_log import log_decision
from intelligence.automation_engine import evaluate_catalog, seed_default_rules

router = APIRouter(tags=["actions", "automations"])


class ActionDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "SNOOZED"]
    actor: str = Field(default="Seller Operator", min_length=1, max_length=128)
    reason: Optional[str] = None
    snooze_days: Optional[int] = Field(default=7, ge=1, le=90)


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=128)
    rule_type: str = Field(min_length=3, max_length=64)
    condition_json: Dict[str, Any] = Field(default_factory=dict)
    action_json: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    cooldown_hours: int = Field(default=24, ge=1, le=720)


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    cooldown_hours: Optional[int] = Field(default=None, ge=1, le=720)
    condition_json: Optional[Dict[str, Any]] = None
    action_json: Optional[Dict[str, Any]] = None


# =====================================================================
# Action Queue / Approval Inbox Endpoints
# =====================================================================

@router.get("/actions")
def list_actions(
    status: Optional[str] = Query(default=None, description="QUEUED, APPROVED, REJECTED, SNOOZED"),
    product_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists draft and decided items in the Seller Control Room Action Center."""
    query = select(ActionQueueItem)

    if status:
        query = query.where(ActionQueueItem.status == status.upper())
    if product_id:
        query = query.where(ActionQueueItem.product_id == product_id)

    query = query.order_by(desc(ActionQueueItem.id)).limit(limit)
    items = session.scalars(query).all()

    # Pre-fetch products for name & asin lookup
    product_ids = {it.product_id for it in items}
    prods = {}
    if product_ids:
        prods = {p.product_id: p for p in session.scalars(select(Product).where(Product.product_id.in_(product_ids))).all()}

    results = []
    now_utc = datetime.now(timezone.utc)
    for it in items:
        # Check if snoozed item is still active snooze
        current_status = it.status
        if current_status == "SNOOZED" and it.snoozed_until:
            s_until = it.snoozed_until
            if s_until.tzinfo is None:
                s_until = s_until.replace(tzinfo=timezone.utc)
            if s_until <= now_utc:
                current_status = "QUEUED"  # Snooze expired, back in active inbox

        prod = prods.get(it.product_id)
        results.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": prod.name if prod else it.product_id,
            "asin": prod.asin if prod else None,
            "category": prod.category if prod else None,
            "action_type": it.action_type,
            "title": it.title,
            "description": it.description,
            "payload": it.payload,
            "status": current_status,
            "why_panel": it.why_panel,
            "snoozed_until": it.snoozed_until.isoformat() if it.snoozed_until else None,
            "created_at": it.created_at.isoformat() if it.created_at else None,
            "updated_at": it.updated_at.isoformat() if it.updated_at else None,
        })
    return results


@router.post("/actions/{action_id}/decide")
def decide_action(
    action_id: int,
    body: ActionDecisionRequest,
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Records human operator approval, rejection, or snooze of an action item."""
    item = session.get(ActionQueueItem, action_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item with ID {action_id} not found."
        )

    previous_status = item.status
    decision = body.decision.upper()
    item.status = decision

    if decision == "SNOOZED":
        days = body.snooze_days or 7
        item.snoozed_until = datetime.now(timezone.utc) + timedelta(days=days)
    else:
        item.snoozed_until = None

    prod = session.get(Product, item.product_id)
    prod_name = prod.name if prod else item.product_id

    # Record Audit Event
    audit_event = AuditEvent(
        event_type=f"ACTION_{decision}",
        actor=body.actor,
        action=f"Decided {decision} for {item.action_type}",
        details={
            "action_id": item.id,
            "product_id": item.product_id,
            "product_name": prod_name,
            "action_type": item.action_type,
            "previous_status": previous_status,
            "new_status": decision,
            "reason": body.reason,
            "snooze_days": body.snooze_days if decision == "SNOOZED" else None,
            "payload": item.payload,
        },
    )
    session.add(audit_event)
    session.commit()

    # Also log to decision_log for backwards compatibility
    log_decision(
        agent=body.actor,
        product_name=prod_name,
        action=f"action_{decision.lower()}",
        detail={
            "action_id": item.id,
            "action_type": item.action_type,
            "reason": body.reason,
        },
    )

    return {
        "success": True,
        "action_id": item.id,
        "status": item.status,
        "snoozed_until": item.snoozed_until.isoformat() if item.snoozed_until else None,
        "audit_event_id": audit_event.id,
    }


# =====================================================================
# Automations Management Endpoints
# =====================================================================

@router.get("/automations/rules")
def get_automation_rules(
    session: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists configured catalog automation rules, seeding defaults if empty."""
    rules = seed_default_rules(session)
    return [
        {
            "id": r.id,
            "name": r.name,
            "rule_type": r.rule_type,
            "condition_json": r.condition_json,
            "action_json": r.action_json,
            "enabled": r.enabled,
            "cooldown_hours": r.cooldown_hours,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rules
    ]


@router.post("/automations/rules", status_code=status.HTTP_201_CREATED)
def create_automation_rule(
    body: AutomationRuleCreate,
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Creates a new automated monitoring and draft rule."""
    rule = AutomationRule(
        name=body.name,
        rule_type=body.rule_type,
        condition_json=body.condition_json,
        action_json=body.action_json,
        enabled=body.enabled,
        cooldown_hours=body.cooldown_hours,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return {
        "id": rule.id,
        "name": rule.name,
        "rule_type": rule.rule_type,
        "condition_json": rule.condition_json,
        "action_json": rule.action_json,
        "enabled": rule.enabled,
        "cooldown_hours": rule.cooldown_hours,
    }


@router.patch("/automations/rules/{rule_id}")
def update_automation_rule(
    rule_id: int,
    body: AutomationRuleUpdate,
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Updates rule configuration, thresholds, or enabled status."""
    rule = session.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Automation rule {rule_id} not found."
        )

    if body.name is not None:
        rule.name = body.name
    if body.enabled is not None:
        rule.enabled = body.enabled
    if body.cooldown_hours is not None:
        rule.cooldown_hours = body.cooldown_hours
    if body.condition_json is not None:
        rule.condition_json = body.condition_json
    if body.action_json is not None:
        rule.action_json = body.action_json

    session.commit()
    session.refresh(rule)
    return {
        "id": rule.id,
        "name": rule.name,
        "rule_type": rule.rule_type,
        "condition_json": rule.condition_json,
        "action_json": rule.action_json,
        "enabled": rule.enabled,
        "cooldown_hours": rule.cooldown_hours,
    }


@router.post("/automations/evaluate")
def run_automation_evaluation(
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Evaluates all catalog products against active rules, generating new draft actions."""
    new_actions = evaluate_catalog(session)
    return {
        "success": True,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "new_actions_count": len(new_actions),
        "actions": [
            {
                "id": a.id,
                "product_id": a.product_id,
                "action_type": a.action_type,
                "title": a.title,
                "why_panel": a.why_panel,
            }
            for a in new_actions
        ],
    }


# =====================================================================
# Audit Log Endpoints
# =====================================================================

@router.get("/audit/events")
def list_audit_events(
    event_type: Optional[str] = Query(default=None),
    actor: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves immutable audit event history for compliance and governance."""
    query = select(AuditEvent)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if actor:
        query = query.where(AuditEvent.actor == actor)

    query = query.order_by(desc(AuditEvent.id)).limit(limit)
    events = session.scalars(query).all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "actor": e.actor,
            "action": e.action,
            "details": e.details,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in events
    ]
