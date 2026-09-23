"""
inventory_engine.py — deterministic Inventory Intelligence calculations.
Pure functions: no I/O, no LLM, no randomness. Reads the same
daily_metrics history the existing inventory_stockout signal detector
uses (units_sold, inventory_level) — no new inventory FACTS are invented,
only a small config layer (lead time, safety days, MOQ) is new.

Every function that can't produce a real answer from the given inputs
returns None rather than fabricating a number — callers must surface that
as "insufficient data," per the project's data-integrity rule.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TypedDict


class DemandStats(TypedDict):
    avg_7d: float
    avg_14d: float
    avg_30d: float
    weighted_avg: float


def compute_demand(daily_units: list[int]) -> DemandStats:
    """daily_units must be ordered oldest -> newest."""

    def _avg(n: int) -> float:
        window = daily_units[-n:] if len(daily_units) >= n else daily_units
        return round(sum(window) / len(window), 2) if window else 0.0

    def _weighted(units: list[int]) -> float:
        # Most recent 7 days weighted 3x, prior 7 weighted 2x, the rest 1x
        # — recent demand matters more for reorder decisions than a flat
        # historical average would suggest.
        if not units:
            return 0.0
        recent = units[-7:]
        mid = units[-14:-7] if len(units) >= 14 else []
        rest = units[:-14] if len(units) > 14 else []
        total_value = sum(u * 3 for u in recent) + sum(u * 2 for u in mid) + sum(u * 1 for u in rest)
        total_weight = len(recent) * 3 + len(mid) * 2 + len(rest) * 1
        return round(total_value / total_weight, 2) if total_weight else 0.0

    return DemandStats(avg_7d=_avg(7), avg_14d=_avg(14), avg_30d=_avg(30), weighted_avg=_weighted(daily_units))


def days_of_cover(available_inventory: int, avg_daily_demand: float) -> float | None:
    if avg_daily_demand <= 0:
        return None
    return round(available_inventory / avg_daily_demand, 1)


def safety_stock(avg_daily_demand: float, safety_days: int) -> float:
    return round(avg_daily_demand * safety_days, 1)


def reorder_point(avg_daily_demand: float, lead_time_days: int, safety_days: int) -> float:
    lead_time_demand = avg_daily_demand * lead_time_days
    return round(lead_time_demand + safety_stock(avg_daily_demand, safety_days), 1)


def suggested_reorder_quantity(
    avg_daily_demand: float,
    current_inventory: int,
    target_days_of_stock: int = 45,
    moq: int | None = None,
    reorder_multiple: int | None = None,
) -> int:
    if avg_daily_demand <= 0:
        return 0
    target_stock_level = avg_daily_demand * target_days_of_stock
    raw_qty = max(0.0, target_stock_level - current_inventory)
    if moq and raw_qty > 0:
        raw_qty = max(raw_qty, moq)
    if reorder_multiple and raw_qty > 0:
        raw_qty = ((int(raw_qty) + reorder_multiple - 1) // reorder_multiple) * reorder_multiple
    return int(round(raw_qty))


def classify_inventory(
    days_cover: float | None,
    avg_daily_demand: float,
    current_inventory: int,
    reorder_point_value: float,
) -> str:
    if days_cover is None:
        return "NO_DATA"
    if current_inventory <= reorder_point_value:
        return "STOCKOUT_RISK" if days_cover <= 5 else "LOW_COVER"
    # Near-zero demand is the more fundamental signal than "too much
    # stock" -- a product selling 0.3 units/day with 200 days of cover is
    # slow-moving, not simply overstocked against otherwise-healthy demand.
    if avg_daily_demand < 0.5:
        return "SLOW_MOVING"
    if days_cover > 90:
        return "OVERSTOCK"
    return "HEALTHY"


def projected_stockout_date(current_inventory: int, avg_daily_demand: float) -> str | None:
    dc = days_of_cover(current_inventory, avg_daily_demand)
    if dc is None:
        return None
    return (date.today() + timedelta(days=int(dc))).isoformat()


def forecast_inventory(
    current_inventory: int,
    avg_daily_demand: float,
    days_ahead: int = 30,
    inbound: list[dict] | None = None,  # [{"day_offset": int, "quantity": int}]
) -> list[dict]:
    """Every row here is PROJECTED, never historical — callers must not
    render this as though it were actual observed inventory."""
    inbound = inbound or []
    inbound_by_day: dict[int, int] = {}
    for item in inbound:
        inbound_by_day[item["day_offset"]] = inbound_by_day.get(item["day_offset"], 0) + item["quantity"]

    today = date.today()
    balance = float(current_inventory)
    rows = []
    for day_offset in range(days_ahead + 1):
        if day_offset > 0:
            balance = max(0.0, balance - avg_daily_demand)
            balance += inbound_by_day.get(day_offset, 0)
        rows.append(
            {
                "day_offset": day_offset,
                "date": (today + timedelta(days=day_offset)).isoformat(),
                "projected_inventory": round(balance, 1),
                "inbound_qty": inbound_by_day.get(day_offset, 0),
            }
        )
    return rows


def what_if_scenario(
    current_inventory: int,
    avg_daily_demand: float,
    reorder_quantity: int,
    lead_time_days: int,
) -> dict:
    """SIMULATION only — the caller must label it as such, never as an
    actual result."""
    inventory_at_arrival = max(0.0, current_inventory - avg_daily_demand * lead_time_days)
    post_replenishment_inventory = inventory_at_arrival + reorder_quantity
    return {
        "lead_time_days": lead_time_days,
        "reorder_quantity": reorder_quantity,
        "inventory_at_arrival": round(inventory_at_arrival, 1),
        "post_replenishment_inventory": round(post_replenishment_inventory, 1),
        "days_of_cover_after_replenishment": days_of_cover(int(post_replenishment_inventory), avg_daily_demand),
        "stockout_risk_before_arrival": inventory_at_arrival <= 0,
    }


def excess_inventory_estimate(current_inventory: int, avg_daily_demand: float, days_cover: float | None) -> dict | None:
    if days_cover is None or days_cover <= 90:
        return None
    expected_stock_for_90_days = avg_daily_demand * 90
    return {
        "current_units": current_inventory,
        "expected_demand_90d": round(expected_stock_for_90_days, 1),
        "days_of_cover": days_cover,
        "excess_units_estimate": round(current_inventory - expected_stock_for_90_days, 1),
    }
