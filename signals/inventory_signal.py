"""
inventory_signal.py — deterministic stockout-risk detector.

Reads FAKE seller-account data only (see CLAUDE.md's "two halves that
must never mix" rule). Flags products where current inventory covers
fewer days than a threshold, given recent sales velocity — a cheap
rule check evaluated deterministically, no LLM.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "db"))
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))
import db  # noqa: E402
from decision_log import log_decision  # noqa: E402

VELOCITY_WINDOW_DAYS = 14
DAYS_OF_STOCK_THRESHOLD = 10


def _days_of_stock_remaining(recent_units_sold: list[int], current_inventory: int) -> float | None:
    avg_daily_sales = sum(recent_units_sold) / len(recent_units_sold) if recent_units_sold else 0
    if avg_daily_sales <= 0:
        return None
    return current_inventory / avg_daily_sales


def check_inventory_signal(product_id: str) -> dict | None:
    rows = db.get_metrics_for_product(product_id)
    if len(rows) < VELOCITY_WINDOW_DAYS:
        return None

    recent = rows[-VELOCITY_WINDOW_DAYS:]
    recent_units_sold = [r["units_sold"] for r in recent]
    current_inventory = rows[-1]["inventory_level"]

    days_remaining = _days_of_stock_remaining(recent_units_sold, current_inventory)
    if days_remaining is None or days_remaining >= DAYS_OF_STOCK_THRESHOLD:
        return None

    severity = "high" if days_remaining <= 3 else "medium"
    return {
        "days_of_stock_remaining": round(days_remaining, 1),
        "current_inventory": current_inventory,
        "avg_daily_sales_last_14d": round(sum(recent_units_sold) / len(recent_units_sold), 2),
        "threshold_days": DAYS_OF_STOCK_THRESHOLD,
        "severity": severity,
        "as_of_date": rows[-1]["date"],
    }


def run_inventory_signal_for_all_products() -> int:
    flagged = 0
    for product in db.get_products():
        evidence = check_inventory_signal(product["product_id"])
        if evidence is None:
            continue
        flagged += 1
        db.insert_detected_signal(
            product_id=product["product_id"],
            date=evidence["as_of_date"],
            signal_type="inventory_stockout",
            severity=evidence["severity"],
            evidence=evidence,
            detected_at=datetime.now(timezone.utc).isoformat(),
        )
        log_decision(
            agent="inventory_signal",
            product_name=product["name"],
            action="signal_detected",
            detail=evidence,
        )
    return flagged


if __name__ == "__main__":
    db.init_db()
    count = run_inventory_signal_for_all_products()
    print(f"Inventory stockout signal: {count} product(s) flagged.")
