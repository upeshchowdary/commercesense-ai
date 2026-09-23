from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from api import deps  # noqa: F401

import db
from inventory_signal import run_inventory_signal_for_all_products
from ppc_waste_signal import run_ppc_waste_signal_for_all_products
from rank_bb_signal import run_rank_bb_signal_for_all_products

router = APIRouter(tags=["signals"])

# Detection wipes and rebuilds the whole detected_signals table
# (db.clear_detected_signals). Two overlapping runs — e.g. a double
# click, or someone loading Evaluation mid-run — would otherwise race
# on that wipe and leave the table in a partial, misleading state.
_run_lock = threading.Lock()

Severity = Literal["high", "medium"]
SignalType = Literal["inventory_stockout", "ppc_waste", "rank_drop"]


@router.post("/signals/run")
def run_signal_detection() -> dict:
    """Mirrors the old Streamlit dashboard's button handler exactly:
    clear everything, re-run all three deterministic detectors."""
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Signal detection is already running")
    try:
        db.clear_detected_signals()
        inventory_count = run_inventory_signal_for_all_products()
        ppc_count = run_ppc_waste_signal_for_all_products()
        rank_count = run_rank_bb_signal_for_all_products()
        return {
            "inventory_stockout_flagged": inventory_count,
            "ppc_waste_flagged": ppc_count,
            "rank_drop_flagged": rank_count,
            "total_flagged": inventory_count + ppc_count + rank_count,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        _run_lock.release()


@router.get("/signals")
def list_signals(
    severity: Severity | None = Query(default=None),
    type: SignalType | None = Query(default=None, alias="type"),
    product_id: str | None = Query(default=None),
) -> list[dict]:
    products = {p["product_id"]: p["name"] for p in db.get_products()}
    rows = db.get_detected_signals(product_id)
    result = []
    for row in rows:
        if severity and row["severity"] != severity:
            continue
        if type and row["signal_type"] != type:
            continue
        d = dict(row)
        d["evidence"] = json.loads(d["evidence"])
        d["product_name"] = products.get(d["product_id"], d["product_id"])
        result.append(d)
    return result


@router.get("/signals/{signal_id}")
def get_signal(signal_id: int) -> dict:
    products = {p["product_id"]: p["name"] for p in db.get_products()}
    for row in db.get_detected_signals():
        if row["id"] == signal_id:
            d = dict(row)
            d["evidence"] = json.loads(d["evidence"])
            d["product_name"] = products.get(d["product_id"], d["product_id"])
            return d
    raise HTTPException(status_code=404, detail="Signal not found")
