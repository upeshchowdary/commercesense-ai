"""
automation_engine.py — Rules Evaluator and Action Generator for CommerceSense AI v3.

Follows strict human-in-the-loop principles:
1. Automated rules evaluate events across the catalog (Buy Box lost, stockout risk,
   excess inventory, negative review spikes, competitor margin floor breaches).
2. Write actions create drafts in the Action Center (action_queue table) requiring
   explicit human approval. Zero autonomous writes to live seller accounts.
3. Debouncing & Cooldowns: Enforces a 24-hour default cooldown per product/rule to
   prevent notification storms.
4. Itemized "Why Panel" included on every queued action item (event, evidence,
   financial impact at current volume, alternatives considered, confidence).
"""

from __future__ import annotations

import decimal
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from db.models import (
    Product,
    DailyMetric,
    PricingData,
    PricingObservation,
    ReviewAnalysis,
    ReviewItem,
    InventoryConfig,
    AutomationRule,
    ActionQueueItem,
    AuditEvent,
)
from intelligence.inventory_engine import (
    compute_demand,
    days_of_cover,
    suggested_reorder_quantity,
)
from intelligence.pricing_engine import (
    minimum_viable_price,
    target_margin_price,
    breakeven_price,
    cost_complete_fixed_unit_cost,
    filter_direct_competitor_observations,
)


DEFAULT_RULES = [
    {
        "name": "Buy Box Loss Protection",
        "rule_type": "BUY_BOX_MONITOR",
        "condition_json": {"event": "BUY_BOX_LOST"},
        "action_json": {"action_type": "PRICE_ADJUSTMENT", "auto_queue": True},
        "enabled": True,
        "cooldown_hours": 24,
    },
    {
        "name": "Critical Stockout Warning (<14 Days)",
        "rule_type": "STOCKOUT_RISK",
        "condition_json": {"days_of_cover_threshold": 14},
        "action_json": {"action_type": "REORDER_INVENTORY", "auto_queue": True},
        "enabled": True,
        "cooldown_hours": 24,
    },
    {
        "name": "Excess Inventory Alert (>90 Days)",
        "rule_type": "EXCESS_INVENTORY",
        "condition_json": {"days_of_cover_threshold": 90},
        "action_json": {"action_type": "LIQUIDATE_OR_DISCOUNT", "auto_queue": True},
        "enabled": True,
        "cooldown_hours": 24,
    },
    {
        "name": "Negative Review Spike Alert (>25%)",
        "rule_type": "NEGATIVE_SPIKE",
        "condition_json": {"negative_pct_threshold": 25.0},
        "action_json": {"action_type": "REVIEW_DEFENSE", "auto_queue": True},
        "enabled": True,
        "cooldown_hours": 24,
    },
    {
        "name": "Competitor Margin Floor Breach Defense",
        "rule_type": "MARGIN_FLOOR_BREACH",
        "condition_json": {"enforce_floor": True},
        "action_json": {"action_type": "PRICE_FLOOR_DEFENSE", "auto_queue": True},
        "enabled": True,
        "cooldown_hours": 24,
    },
]


def seed_default_rules(session: Session) -> List[AutomationRule]:
    """Seeds standard automation rules if none are present."""
    existing = session.scalars(select(AutomationRule)).all()
    if existing:
        return list(existing)

    rules = []
    for r_data in DEFAULT_RULES:
        rule = AutomationRule(
            name=r_data["name"],
            rule_type=r_data["rule_type"],
            condition_json=r_data["condition_json"],
            action_json=r_data["action_json"],
            enabled=r_data["enabled"],
            cooldown_hours=r_data["cooldown_hours"],
        )
        session.add(rule)
        rules.append(rule)
    session.commit()
    return rules


def is_rule_in_cooldown(
    session: Session,
    product_id: str,
    action_type: str,
    cooldown_hours: int = 24,
) -> bool:
    """Checks whether an action item of this action_type for product_id was created within cooldown_hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
    # Filter in python or query (handling timezone naive/aware timestamps)
    recent_items = session.scalars(
        select(ActionQueueItem)
        .where(
            ActionQueueItem.product_id == product_id,
            ActionQueueItem.action_type == action_type,
        )
        .order_by(desc(ActionQueueItem.created_at))
    ).all()

    for item in recent_items:
        created = item.created_at
        if created is not None:
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created >= cutoff:
                return True
    return False


def evaluate_product_buy_box(
    product: Product,
    session: Session,
    cooldown_hours: int = 24,
) -> Optional[ActionQueueItem]:
    """Evaluates whether product lost Buy Box and generates price adjustment draft."""
    if is_rule_in_cooldown(session, product.product_id, "PRICE_ADJUSTMENT", cooldown_hours):
        return None

    # Get latest metrics
    latest_metrics = session.scalars(
        select(DailyMetric)
        .where(DailyMetric.product_id == product.product_id)
        .order_by(desc(DailyMetric.date))
        .limit(3)
    ).all()

    if not latest_metrics:
        return None

    latest_m = latest_metrics[0]
    has_bb = latest_m.has_buy_box

    # Check competitor observations for buy box winner
    competitor_obs = session.scalars(
        select(PricingObservation)
        .where(PricingObservation.product_id == product.product_id)
        .order_by(desc(PricingObservation.observed_at))
    ).all()

    bb_winner_obs = None
    for obs in competitor_obs:
        if obs.is_buy_box_winner and obs.competitor != "Seller":
            bb_winner_obs = obs
            break

    if has_bb and bb_winner_obs is None:
        return None

    # We lost Buy Box!
    pricing = session.get(PricingData, product.product_id)
    current_price = float(product.base_price)
    
    # Calculate min margin floor and target margin price
    min_floor = None
    target_price = None
    if pricing:
        min_floor = float(minimum_viable_price(
            cogs=pricing.cogs,
            fulfillment_fee=pricing.fulfillment_fee,
            referral_fee_pct=pricing.referral_fee_pct,
            min_margin_pct=pricing.min_margin_pct,
            closing_fee=pricing.closing_fee,
            packaging_cost=pricing.packaging_cost,
            inbound_freight=pricing.inbound_freight,
            ad_cost_per_unit=pricing.ad_cost_per_unit,
            returns_allowance=pricing.returns_allowance,
            other_cost=pricing.other_cost,
        ))
        target_price = float(target_margin_price(
            cogs=pricing.cogs,
            fulfillment_fee=pricing.fulfillment_fee,
            referral_fee_pct=pricing.referral_fee_pct,
            target_margin_pct=pricing.target_margin_pct,
            closing_fee=pricing.closing_fee,
            packaging_cost=pricing.packaging_cost,
            inbound_freight=pricing.inbound_freight,
            ad_cost_per_unit=pricing.ad_cost_per_unit,
            returns_allowance=pricing.returns_allowance,
            other_cost=pricing.other_cost,
        ))

    comp_price = float(bb_winner_obs.landed_price or bb_winner_obs.price) if bb_winner_obs else round(current_price * 0.95, 2)
    comp_name = bb_winner_obs.competitor if bb_winner_obs else "Direct Competitor"

    # Constrained recommendation: cannot go below min_floor
    rec_price = comp_price
    floor_breached = False
    if min_floor and comp_price < min_floor:
        rec_price = min_floor
        floor_breached = True

    recent_units = [m.units_sold for m in reversed(latest_metrics)]
    velocity = float(sum(recent_units) / max(len(recent_units), 1))
    daily_impact = round(velocity * (current_price - rec_price), 2) if not floor_breached else round(velocity * (current_price * 0.5), 2)

    why_panel = {
        "event": "BUY_BOX_LOST",
        "evidence": {
            "current_price": current_price,
            "competitor_price": comp_price,
            "competitor_name": comp_name,
            "seller_has_buy_box": False,
            "minimum_viable_floor": min_floor,
            "target_margin_price": target_price,
            "daily_velocity_units": round(velocity, 1),
        },
        "financial_impact_at_current_volume": (
            f"Competitor winning Buy Box at ${comp_price:.2f}. "
            f"Estimated daily revenue exposure: -${daily_impact:.2f} at observed velocity of {velocity:.1f} units/day."
        ),
        "alternatives_considered": [
            f"Reprice to match Buy Box winner at ${comp_price:.2f}" if not floor_breached else f"Hold at margin floor ${min_floor:.2f} (DO NOT match below floor)",
            f"Maintain price at ${current_price:.2f} and rely on brand equity / FBA speed",
            "Deploy a 5% instant clip coupon to improve conversion without lowering catalog list price",
        ],
        "confidence": "high",
    }

    action_item = ActionQueueItem(
        product_id=product.product_id,
        action_type="PRICE_ADJUSTMENT",
        title=f"Adjust price to ${rec_price:.2f} for {product.name[:40]}",
        description=f"Lost Buy Box to {comp_name} (${comp_price:.2f}). Proposed new price is ${rec_price:.2f}.",
        payload={
            "product_id": product.product_id,
            "current_price": current_price,
            "proposed_price": rec_price,
            "competitor_price": comp_price,
            "competitor": comp_name,
            "floor_breached": floor_breached,
        },
        status="QUEUED",
        why_panel=why_panel,
    )
    return action_item


def evaluate_product_inventory(
    product: Product,
    session: Session,
    stockout_threshold: int = 14,
    excess_threshold: int = 90,
    cooldown_hours: int = 24,
) -> List[ActionQueueItem]:
    """Evaluates stockout risk and excess inventory for a product."""
    actions: List[ActionQueueItem] = []

    metrics = session.scalars(
        select(DailyMetric)
        .where(DailyMetric.product_id == product.product_id)
        .order_by(DailyMetric.date)
    ).all()

    if not metrics:
        return actions

    current_inv = metrics[-1].inventory_level
    daily_units = [m.units_sold for m in metrics]
    demand_stats = compute_demand(daily_units)
    avg_demand = demand_stats["weighted_avg"] or demand_stats["avg_7d"]

    doc = days_of_cover(current_inv, avg_demand)
    if doc is None:
        return actions

    config = session.get(InventoryConfig, product.product_id)
    lead_time = config.lead_time_days if config else 14
    safety_days = config.safety_days if config else 7
    moq = config.moq if config else None
    reorder_multiple = config.reorder_multiple if config else None

    # 1. Stockout Risk
    if doc <= stockout_threshold:
        if not is_rule_in_cooldown(session, product.product_id, "REORDER_INVENTORY", cooldown_hours):
            reorder_qty = suggested_reorder_quantity(
                avg_daily_demand=avg_demand,
                current_inventory=current_inv,
                target_days_of_stock=max(45, lead_time + safety_days + 15),
                moq=moq,
                reorder_multiple=reorder_multiple,
            )
            unit_cogs = 0.0
            pricing = session.get(PricingData, product.product_id)
            if pricing:
                unit_cogs = float(pricing.cogs)
            est_order_cost = round(reorder_qty * unit_cogs, 2)
            rev_at_risk = round(avg_demand * lead_time * float(product.base_price), 2)

            why_panel = {
                "event": "STOCKOUT_RISK",
                "evidence": {
                    "current_inventory": current_inv,
                    "days_of_cover": doc,
                    "avg_daily_demand": avg_demand,
                    "lead_time_days": lead_time,
                    "safety_days": safety_days,
                    "threshold_days": stockout_threshold,
                },
                "financial_impact_at_current_volume": (
                    f"Only {doc:.1f} days of cover remaining against a {lead_time}-day supplier lead time. "
                    f"Projected revenue at risk: ${rev_at_risk:.2f} during expected stockout."
                ),
                "alternatives_considered": [
                    f"Create Purchase Order for {reorder_qty} units (est. cost ${est_order_cost:.2f})",
                    "Expedite half-batch via Air Freight (7-day lead time) to avoid stockout gap",
                    "Increase selling price by 5-10% immediately to temper run-rate and stretch stock",
                ],
                "confidence": "high",
            }

            actions.append(ActionQueueItem(
                product_id=product.product_id,
                action_type="REORDER_INVENTORY",
                title=f"Create Restock Order ({reorder_qty} units) for {product.name[:40]}",
                description=f"Stockout risk: {doc:.1f} days cover vs {lead_time} days lead time. Recommended reorder: {reorder_qty} units.",
                payload={
                    "product_id": product.product_id,
                    "recommended_reorder_qty": reorder_qty,
                    "current_inventory": current_inv,
                    "days_of_cover": doc,
                    "estimated_order_cost": est_order_cost,
                    "lead_time_days": lead_time,
                },
                status="QUEUED",
                why_panel=why_panel,
            ))

    # 2. Excess Inventory
    elif doc >= excess_threshold:
        if not is_rule_in_cooldown(session, product.product_id, "LIQUIDATE_OR_DISCOUNT", cooldown_hours):
            excess_units = max(0, int(current_inv - (avg_demand * 45)))
            monthly_fba_storage = round(excess_units * 0.85, 2)

            why_panel = {
                "event": "EXCESS_INVENTORY",
                "evidence": {
                    "current_inventory": current_inv,
                    "days_of_cover": doc,
                    "excess_units_above_45d": excess_units,
                    "threshold_days": excess_threshold,
                },
                "financial_impact_at_current_volume": (
                    f"{doc:.1f} days of cover exceeds healthy 45-day baseline. "
                    f"Estimated monthly holding cost: ~${monthly_fba_storage:.2f}."
                ),
                "alternatives_considered": [
                    "Run 15% limited-time promotional discount to accelerate run-rate",
                    "Bundle excess inventory with top-selling complementary product",
                    "Submit FBA removal or liquidation order for aged stock",
                ],
                "confidence": "medium",
            }

            actions.append(ActionQueueItem(
                product_id=product.product_id,
                action_type="LIQUIDATE_OR_DISCOUNT",
                title=f"Excess Inventory Plan: {excess_units} units for {product.name[:40]}",
                description=f"{doc:.1f} days of cover detected. Consider running a promotional discount to prevent long-term storage fees.",
                payload={
                    "product_id": product.product_id,
                    "current_inventory": current_inv,
                    "days_of_cover": doc,
                    "excess_units": excess_units,
                    "estimated_monthly_storage_fee": monthly_fba_storage,
                },
                status="QUEUED",
                why_panel=why_panel,
            ))

    return actions


def evaluate_product_reviews(
    product: Product,
    session: Session,
    negative_threshold: float = 25.0,
    cooldown_hours: int = 24,
) -> Optional[ActionQueueItem]:
    """Evaluates whether product has a negative review spike or critical emerging issue."""
    if is_rule_in_cooldown(session, product.product_id, "REVIEW_DEFENSE", cooldown_hours):
        return None

    # Check latest review analysis
    analysis = session.scalars(
        select(ReviewAnalysis)
        .where(ReviewAnalysis.product_id == product.product_id)
        .order_by(desc(ReviewAnalysis.analyzed_at))
    ).first()

    if not analysis:
        # Check review items directly
        reviews = session.scalars(
            select(ReviewItem).where(ReviewItem.product_id == product.product_id)
        ).all()
        if not reviews or len(reviews) < 5:
            return None
        neg_count = sum(1 for r in reviews if r.rating in (1, 2))
        neg_pct = (neg_count / len(reviews)) * 100.0
        emerging = []
    else:
        neg_pct = float(analysis.negative_pct)
        emerging = analysis.emerging_issues or []

    if neg_pct < negative_threshold and not emerging:
        return None

    why_panel = {
        "event": "NEGATIVE_SPIKE",
        "evidence": {
            "negative_pct": round(neg_pct, 1),
            "threshold": negative_threshold,
            "emerging_issues": emerging[:3],
            "total_reviews_analyzed": analysis.total_reviews if analysis else len(reviews),
        },
        "financial_impact_at_current_volume": (
            f"Negative review rate is {neg_pct:.1f}% (threshold {negative_threshold}%). "
            f"Risk of star rating decay impacting listing conversion rate by 15-25%."
        ),
        "alternatives_considered": [
            "Update listing bullets and description to clarify customer expectations",
            "Audit supplier batch quality control for recurring defect patterns",
            "Implement post-purchase packaging insert with clear instructions",
        ],
        "confidence": "high",
    }

    return ActionQueueItem(
        product_id=product.product_id,
        action_type="REVIEW_DEFENSE",
        title=f"Review Quality Alert ({neg_pct:.1f}% neg) for {product.name[:40]}",
        description=f"Negative review rate spiked to {neg_pct:.1f}%. Emerging issues: {', '.join([str(e) for e in emerging[:2]]) or 'Customer dissatisfaction'}.",
        payload={
            "product_id": product.product_id,
            "negative_pct": neg_pct,
            "emerging_issues": emerging,
        },
        status="QUEUED",
        why_panel=why_panel,
    )


def evaluate_product_margin_floor(
    product: Product,
    session: Session,
    cooldown_hours: int = 24,
) -> Optional[ActionQueueItem]:
    """Evaluates whether competitors are breaching the minimum viable margin floor."""
    if is_rule_in_cooldown(session, product.product_id, "PRICE_FLOOR_DEFENSE", cooldown_hours):
        return None

    pricing = session.get(PricingData, product.product_id)
    if not pricing:
        return None

    min_floor = float(minimum_viable_price(
        cogs=pricing.cogs,
        fulfillment_fee=pricing.fulfillment_fee,
        referral_fee_pct=pricing.referral_fee_pct,
        min_margin_pct=pricing.min_margin_pct,
        closing_fee=pricing.closing_fee,
        packaging_cost=pricing.packaging_cost,
        inbound_freight=pricing.inbound_freight,
        ad_cost_per_unit=pricing.ad_cost_per_unit,
        returns_allowance=pricing.returns_allowance,
        other_cost=pricing.other_cost,
    ))

    # Check direct competitor observations
    observations = session.scalars(
        select(PricingObservation).where(PricingObservation.product_id == product.product_id)
    ).all()
    if not observations:
        return None

    obs_dicts = [
        {
            "competitor": o.competitor,
            "price": float(o.price),
            "landed_price": float(o.landed_price or o.price),
            "match_tier": o.match_tier,
        }
        for o in observations
    ]
    direct_obs = filter_direct_competitor_observations(obs_dicts)

    breaching_comp = None
    for obs in direct_obs:
        if obs["landed_price"] < min_floor:
            breaching_comp = obs
            break

    if not breaching_comp:
        return None

    comp_name = breaching_comp["competitor"]
    comp_price = breaching_comp["landed_price"]

    why_panel = {
        "event": "MARGIN_FLOOR_BREACH",
        "evidence": {
            "competitor": comp_name,
            "competitor_landed_price": comp_price,
            "seller_minimum_viable_floor": min_floor,
            "seller_current_price": float(product.base_price),
            "cogs": float(pricing.cogs),
            "min_margin_pct": float(pricing.min_margin_pct),
        },
        "financial_impact_at_current_volume": (
            f"Competitor {comp_name} is selling at ${comp_price:.2f}, below your minimum viable floor of ${min_floor:.2f}. "
            f"Matching this price would cause negative unit margin or violate your {float(pricing.min_margin_pct)*100:.0f}% margin threshold."
        ),
        "alternatives_considered": [
            f"Enforce DO_NOT_MATCH policy: maintain price floor at ${min_floor:.2f}",
            "Highlight premium materials / verified reviews to justify price premium",
            "Audit supplier cost breakdown to assess possible COGS reduction",
        ],
        "confidence": "high",
    }

    return ActionQueueItem(
        product_id=product.product_id,
        action_type="PRICE_FLOOR_DEFENSE",
        title=f"Margin Floor Defense for {product.name[:40]}",
        description=f"Competitor {comp_name} is priced at ${comp_price:.2f}, below your floor of ${min_floor:.2f}. DO NOT MATCH recommendation enforced.",
        payload={
            "product_id": product.product_id,
            "competitor": comp_name,
            "competitor_price": comp_price,
            "minimum_viable_floor": min_floor,
            "action": "DO_NOT_MATCH",
        },
        status="QUEUED",
        why_panel=why_panel,
    )


def evaluate_product(
    product: Product,
    session: Session,
    rules: Optional[List[AutomationRule]] = None,
) -> List[ActionQueueItem]:
    """Evaluates all enabled automation rules for a given product."""
    if rules is None:
        rules = session.scalars(
            select(AutomationRule).where(AutomationRule.enabled == True)
        ).all()

    rule_types = {r.rule_type: r for r in rules}
    queued_actions: List[ActionQueueItem] = []

    # 1. Buy Box Monitor
    if "BUY_BOX_MONITOR" in rule_types:
        r = rule_types["BUY_BOX_MONITOR"]
        act = evaluate_product_buy_box(product, session, cooldown_hours=r.cooldown_hours)
        if act:
            queued_actions.append(act)

    # 2. Inventory Rules (Stockout & Excess)
    has_stockout_rule = "STOCKOUT_RISK" in rule_types
    has_excess_rule = "EXCESS_INVENTORY" in rule_types
    if has_stockout_rule or has_excess_rule:
        s_rule = rule_types.get("STOCKOUT_RISK")
        e_rule = rule_types.get("EXCESS_INVENTORY")
        s_thresh = s_rule.condition_json.get("days_of_cover_threshold", 14) if s_rule else 14
        e_thresh = e_rule.condition_json.get("days_of_cover_threshold", 90) if e_rule else 90
        cooldown = s_rule.cooldown_hours if s_rule else (e_rule.cooldown_hours if e_rule else 24)

        inv_actions = evaluate_product_inventory(
            product,
            session,
            stockout_threshold=s_thresh,
            excess_threshold=e_thresh,
            cooldown_hours=cooldown,
        )
        for act in inv_actions:
            if act.action_type == "REORDER_INVENTORY" and has_stockout_rule:
                queued_actions.append(act)
            elif act.action_type == "LIQUIDATE_OR_DISCOUNT" and has_excess_rule:
                queued_actions.append(act)

    # 3. Negative Review Spike
    if "NEGATIVE_SPIKE" in rule_types:
        r = rule_types["NEGATIVE_SPIKE"]
        neg_thresh = float(r.condition_json.get("negative_pct_threshold", 25.0))
        act = evaluate_product_reviews(product, session, negative_threshold=neg_thresh, cooldown_hours=r.cooldown_hours)
        if act:
            queued_actions.append(act)

    # 4. Margin Floor Breach
    if "MARGIN_FLOOR_BREACH" in rule_types:
        r = rule_types["MARGIN_FLOOR_BREACH"]
        act = evaluate_product_margin_floor(product, session, cooldown_hours=r.cooldown_hours)
        if act:
            queued_actions.append(act)

    return queued_actions


def evaluate_catalog(session: Session) -> List[ActionQueueItem]:
    """Scans all products in the catalog against active automation rules,
    persisting generated draft items into the action_queue table.
    """
    seed_default_rules(session)
    active_rules = session.scalars(
        select(AutomationRule).where(AutomationRule.enabled == True)
    ).all()

    products = session.scalars(select(Product)).all()
    created_actions: List[ActionQueueItem] = []

    for prod in products:
        actions = evaluate_product(prod, session, rules=active_rules)
        for action in actions:
            session.add(action)
            created_actions.append(action)

    if created_actions:
        session.commit()

    return created_actions
