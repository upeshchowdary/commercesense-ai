"""
test_forecasting_and_actions.py — Unit and integration tests for:
1. Stockout-censored demand adjustment & rolling-origin StatsForecast evaluation.
2. Automation rule evaluation and debouncing.
3. Action Queue (Approval Inbox) with itemized "Why Panel".
4. Decision recording & immutable audit event logging.
"""

from __future__ import annotations

import decimal
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.main import app
from db.models import (
    Product,
    DailyMetric,
    PricingData,
    PricingObservation,
    AutomationRule,
    ActionQueueItem,
    AuditEvent,
)
from db.session import get_session
from intelligence.forecasting_engine import (
    uncensor_stockout_demand,
    evaluate_backtest_wape,
    evaluate_backtest_mae,
    generate_demand_forecast,
    forecast_product_demand,
)
from intelligence.automation_engine import (
    seed_default_rules,
    is_rule_in_cooldown,
    evaluate_product_buy_box,
    evaluate_product_inventory,
    evaluate_product_margin_floor,
    evaluate_product,
    evaluate_catalog,
)


@pytest.fixture
def test_client():
    return TestClient(app)


# =====================================================================
# 1. Forecasting Engine Tests
# =====================================================================

def test_censored_demand_adjustment():
    """Stockout periods (inventory_level == 0) with zero sales must be imputed
    using the rolling median of in-stock periods to prevent structural underforecasting."""
    history = [
        {"date": "2026-10-01", "units_sold": 10, "inventory_level": 50},
        {"date": "2026-10-02", "units_sold": 12, "inventory_level": 40},
        {"date": "2026-10-03", "units_sold": 11, "inventory_level": 29},
        {"date": "2026-10-04", "units_sold": 0, "inventory_level": 0},   # Stockout!
        {"date": "2026-10-05", "units_sold": 0, "inventory_level": 0},   # Stockout!
        {"date": "2026-10-06", "units_sold": 14, "inventory_level": 100}, # Restocked
        {"date": "2026-10-07", "units_sold": 13, "inventory_level": 86},
    ]

    uncensored, censored_count = uncensor_stockout_demand(history)
    assert len(uncensored) == 7
    assert censored_count == 2

    # During stockouts on day 4 & 5, imputed demand must be > 0 (reflecting in-stock median)
    assert uncensored[3] > 0
    assert uncensored[4] > 0

    # In-stock days preserve original observed sales
    assert uncensored[0] == 10.0
    assert uncensored[5] == 14.0


def test_statsforecast_model_training_and_evaluation():
    """Generates 14-day forecasts with WAPE validation across candidate models."""
    # Synthetic 35-day daily units
    daily_units = [15.0 + (i % 7) * 3.0 for i in range(35)]

    # Forecast generation with internal backtest validation
    forecast_res = generate_demand_forecast(
        daily_units=daily_units,
        horizon_days=14,
        season_length=7,
    )

    assert "selected_model" in forecast_res
    assert forecast_res["selected_model"] in ["SeasonalNaive", "AutoETS", "CrostonClassic", "CrostonSBA", "Naive", "NaiveAverageFallback"]
    assert "backtest_wape" in forecast_res
    assert forecast_res["backtest_wape"] >= 0.0
    assert len(forecast_res["forecast_points"]) == 14
    for pt in forecast_res["forecast_points"]:
        assert "date" in pt
        assert "p50_expected" in pt
        assert pt["p50_expected"] > 0.0


def test_forecast_product_demand_db_integration():
    """Tests end-to-end forecast generation for a product from the database."""
    session = get_session()
    try:
        prod = session.scalars(select(Product)).first()
        assert prod is not None

        res = forecast_product_demand(prod.product_id, session=session, horizon_days=14)
        assert res["product_id"] == prod.product_id
        assert len(res["forecast_points"]) == 14
        assert "selected_model" in res
    finally:
        session.close()


# =====================================================================
# 2. Automation Engine Tests
# =====================================================================

def test_seed_default_rules():
    """Seeds 5 canonical default automation rules."""
    session = get_session()
    try:
        rules = seed_default_rules(session)
        assert len(rules) >= 5
        types = {r.rule_type for r in rules}
        assert "BUY_BOX_MONITOR" in types
        assert "STOCKOUT_RISK" in types
        assert "EXCESS_INVENTORY" in types
        assert "NEGATIVE_SPIKE" in types
        assert "MARGIN_FLOOR_BREACH" in types
    finally:
        session.close()


def test_cooldown_logic():
    """Ensures rules do not produce duplicate actions within cooldown period."""
    session = get_session()
    try:
        prod = session.scalars(select(Product)).first()
        assert prod is not None

        # Clean any existing test items
        existing = session.scalars(
            select(ActionQueueItem).where(
                ActionQueueItem.product_id == prod.product_id,
                ActionQueueItem.action_type == "TEST_COOLDOWN_ACTION",
            )
        ).all()
        for it in existing:
            session.delete(it)
        session.commit()

        # Not in cooldown initially
        assert is_rule_in_cooldown(session, prod.product_id, "TEST_COOLDOWN_ACTION", cooldown_hours=24) is False

        # Add item created now
        action = ActionQueueItem(
            product_id=prod.product_id,
            action_type="TEST_COOLDOWN_ACTION",
            title="Cooldown Test Action",
            description="Testing cooldown logic",
            payload={"test": 123},
            status="QUEUED",
            why_panel={"event": "TEST", "evidence": {}, "financial_impact_at_current_volume": "None", "alternatives_considered": [], "confidence": "high"},
            created_at=datetime.now(timezone.utc),
        )
        session.add(action)
        session.commit()

        # Now must be in cooldown
        assert is_rule_in_cooldown(session, prod.product_id, "TEST_COOLDOWN_ACTION", cooldown_hours=24) is True
    finally:
        session.close()


def test_evaluate_catalog_action_generation():
    """Evaluates entire catalog and generates queued items with Why Panels."""
    session = get_session()
    try:
        new_actions = evaluate_catalog(session)
        # Query all actions in action_queue
        all_actions = session.scalars(select(ActionQueueItem)).all()
        assert len(all_actions) > 0

        sample = all_actions[0]
        assert sample.status in ["QUEUED", "APPROVED", "REJECTED", "SNOOZED"]
        assert sample.why_panel is not None
        assert "event" in sample.why_panel
        assert "evidence" in sample.why_panel
        assert "financial_impact_at_current_volume" in sample.why_panel
        assert "alternatives_considered" in sample.why_panel
        assert isinstance(sample.why_panel["alternatives_considered"], list)
        assert sample.why_panel["confidence"] in ["high", "medium", "low"]
    finally:
        session.close()


# =====================================================================
# 3. Action Decision & Audit Logging API Tests
# =====================================================================

def test_action_decision_lifecycle_api(test_client):
    """Verifies complete approval inbox lifecycle: list -> decide (approve/reject/snooze) -> audit log."""
    # 1. Trigger evaluation to guarantee at least one queued item
    eval_resp = test_client.post("/api/v1/automations/evaluate")
    assert eval_resp.status_code == 200

    # 2. List actions
    list_resp = test_client.get("/api/v1/actions")
    assert list_resp.status_code == 200
    actions = list_resp.json()
    assert isinstance(actions, list)
    assert len(actions) > 0

    target = actions[0]
    action_id = target["id"]

    # 3. Decide: Snooze for 7 days
    snooze_resp = test_client.post(
        f"/api/v1/actions/{action_id}/decide",
        json={
            "decision": "SNOOZED",
            "actor": "Lead Merchandiser",
            "reason": "Supplier shipment in transit, re-evaluate next Monday",
            "snooze_days": 7,
        },
    )
    assert snooze_resp.status_code == 200
    snooze_data = snooze_resp.json()
    assert snooze_data["success"] is True
    assert snooze_data["status"] == "SNOOZED"
    assert snooze_data["snoozed_until"] is not None

    # 4. Decide: Approve
    approve_resp = test_client.post(
        f"/api/v1/actions/{action_id}/decide",
        json={
            "decision": "APPROVED",
            "actor": "Lead Merchandiser",
            "reason": "Authorized price adjustment to defend Buy Box",
        },
    )
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()
    assert approve_data["status"] == "APPROVED"

    # 5. Check Audit Log
    audit_resp = test_client.get("/api/v1/audit/events?limit=10")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    assert len(events) > 0
    latest = events[0]
    assert latest["actor"] == "Lead Merchandiser"
    assert "APPROVED" in latest["event_type"]
    assert latest["details"]["action_id"] == action_id


def test_automation_rules_api(test_client):
    """Verifies automation rules listing and updates."""
    rules_resp = test_client.get("/api/v1/automations/rules")
    assert rules_resp.status_code == 200
    rules = rules_resp.json()
    assert len(rules) >= 5

    rule_id = rules[0]["id"]
    # Toggle enabled / update cooldown
    patch_resp = test_client.patch(
        f"/api/v1/automations/rules/{rule_id}",
        json={"cooldown_hours": 48},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["cooldown_hours"] == 48
