"""
ppc_waste_signal.py — deterministic ad-spend-waste detector.

Flags products where ACOS (ad spend / ad sales) has stayed above a
threshold for a sustained recent stretch, not just a single noisy day.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "db"))
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))
import db  # noqa: E402
from decision_log import log_decision  # noqa: E402

ACOS_THRESHOLD = 0.40
SUSTAINED_WINDOW_DAYS = 10
MIN_DAYS_OVER_THRESHOLD = 7


def _daily_acos(ad_spend: float, ad_sales: float) -> float | None:
    if ad_sales <= 0:
        return None if ad_spend <= 0 else float("inf")
    return ad_spend / ad_sales


def check_ppc_waste_signal(product_id: str) -> dict | None:
    rows = db.get_metrics_for_product(product_id)
    if len(rows) < SUSTAINED_WINDOW_DAYS:
        return None

    recent = rows[-SUSTAINED_WINDOW_DAYS:]
    daily_acos = []
    days_over_threshold = 0
    for r in recent:
        acos = _daily_acos(r["ad_spend"], r["ad_sales"])
        if acos is None:
            continue
        daily_acos.append(acos)
        if acos > ACOS_THRESHOLD:
            days_over_threshold += 1

    if days_over_threshold < MIN_DAYS_OVER_THRESHOLD:
        return None

    avg_acos = sum(daily_acos) / len(daily_acos) if daily_acos else 0
    total_spend = sum(r["ad_spend"] for r in recent)
    total_sales = sum(r["ad_sales"] for r in recent)
    severity = "high" if avg_acos > 0.60 else "medium"

    return {
        "days_over_threshold": days_over_threshold,
        "window_days": SUSTAINED_WINDOW_DAYS,
        "avg_acos_last_window": round(avg_acos, 3),
        "threshold_acos": ACOS_THRESHOLD,
        "total_ad_spend_last_window": round(total_spend, 2),
        "total_ad_sales_last_window": round(total_sales, 2),
        "severity": severity,
        "as_of_date": rows[-1]["date"],
    }


def run_ppc_waste_signal_for_all_products() -> int:
    """Idempotent: clears this signal type's prior rows first, so
    re-running (e.g. a Phase 5 refresh) reflects current data instead
    of accumulating duplicate detections alongside old ones."""
    db.clear_detected_signals_by_type("ppc_waste")
    flagged = 0
    for product in db.get_products():
        evidence = check_ppc_waste_signal(product["product_id"])
        if evidence is None:
            continue
        flagged += 1
        db.insert_detected_signal(
            product_id=product["product_id"],
            date=evidence["as_of_date"],
            signal_type="ppc_waste",
            severity=evidence["severity"],
            evidence=evidence,
            detected_at=datetime.now(timezone.utc).isoformat(),
        )
        log_decision(
            agent="ppc_waste_signal",
            product_name=product["name"],
            action="signal_detected",
            detail=evidence,
        )
    return flagged


if __name__ == "__main__":
    db.init_db()
    count = run_ppc_waste_signal_for_all_products()
    print(f"PPC waste signal: {count} product(s) flagged.")
