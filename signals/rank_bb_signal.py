"""
rank_bb_signal.py — deterministic rank-movement / Buy Box-loss detector.

Flags products where rank has worsened sharply over a recent window,
OR the Buy Box has been lost for a sustained recent stretch — checked
independently so either alone is enough to flag, since they often
share a root cause (a hijacker, a pricing war) but don't always move
together.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "db"))
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))
import db  # noqa: E402
from decision_log import log_decision  # noqa: E402

RANK_WINDOW_DAYS = 14
RANK_WORSENING_THRESHOLD_PCT = 0.50
BUYBOX_WINDOW_DAYS = 10
BUYBOX_LOSS_THRESHOLD_DAYS = 5


def check_rank_bb_signal(product_id: str) -> dict | None:
    rows = db.get_metrics_for_product(product_id)
    if len(rows) < max(RANK_WINDOW_DAYS, BUYBOX_WINDOW_DAYS):
        return None

    rank_window = rows[-RANK_WINDOW_DAYS:]
    rank_start = rank_window[0]["rank"]
    rank_end = rank_window[-1]["rank"]
    rank_pct_change = (rank_end - rank_start) / rank_start if rank_start > 0 else 0

    bb_window = rows[-BUYBOX_WINDOW_DAYS:]
    days_without_buybox = sum(1 for r in bb_window if not r["has_buy_box"])

    rank_flagged = rank_pct_change >= RANK_WORSENING_THRESHOLD_PCT
    bb_flagged = days_without_buybox >= BUYBOX_LOSS_THRESHOLD_DAYS

    if not rank_flagged and not bb_flagged:
        return None

    severity = "high" if (rank_flagged and bb_flagged) else "medium"
    return {
        "rank_flagged": rank_flagged,
        "rank_start": rank_start,
        "rank_end": rank_end,
        "rank_pct_worse": round(rank_pct_change * 100, 1),
        "rank_window_days": RANK_WINDOW_DAYS,
        "buybox_flagged": bb_flagged,
        "days_without_buybox": days_without_buybox,
        "buybox_window_days": BUYBOX_WINDOW_DAYS,
        "severity": severity,
        "as_of_date": rows[-1]["date"],
    }


def run_rank_bb_signal_for_all_products() -> int:
    """Idempotent: clears this signal type's prior rows first, so
    re-running (e.g. a Phase 5 refresh) reflects current data instead
    of accumulating duplicate detections alongside old ones."""
    db.clear_detected_signals_by_type("rank_drop")
    flagged = 0
    for product in db.get_products():
        evidence = check_rank_bb_signal(product["product_id"])
        if evidence is None:
            continue
        flagged += 1
        db.insert_detected_signal(
            product_id=product["product_id"],
            date=evidence["as_of_date"],
            signal_type="rank_drop",
            severity=evidence["severity"],
            evidence=evidence,
            detected_at=datetime.now(timezone.utc).isoformat(),
        )
        log_decision(
            agent="rank_bb_signal",
            product_name=product["name"],
            action="signal_detected",
            detail=evidence,
        )
    return flagged


if __name__ == "__main__":
    db.init_db()
    count = run_rank_bb_signal_for_all_products()
    print(f"Rank/Buy Box signal: {count} product(s) flagged.")
