from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from api import deps

import db
from decision_log import read_decisions

router = APIRouter(tags=["products"])

_LABELED_SET_PATH = deps.PROJECT_ROOT / "eval" / "labeled_set.json"


def _planted_issues() -> dict[str, str | None]:
    if not _LABELED_SET_PATH.exists():
        return {}
    with _LABELED_SET_PATH.open("r", encoding="utf-8") as f:
        labels = json.load(f)
    return {row["product_id"]: row["planted_issue"] for row in labels}


@router.get("/products")
def list_products() -> list[dict]:
    products = db.get_products()
    all_signals = db.get_detected_signals()
    planted = _planted_issues()

    signals_by_product: dict[str, list[dict]] = {}
    for row in all_signals:
        signals_by_product.setdefault(row["product_id"], []).append(dict(row))

    result = []
    for p in products:
        pid = p["product_id"]
        prod_signals = signals_by_product.get(pid, [])
        severities = {s["severity"] for s in prod_signals}
        highest = "high" if "high" in severities else ("medium" if "medium" in severities else None)
        result.append(
            {
                "product_id": pid,
                "name": p["name"],
                "category": p["category"],
                "base_price": p["base_price"],
                "signal_count": len(prod_signals),
                "highest_severity": highest,
                "planted_issue": planted.get(pid),
            }
        )
    return result


@router.get("/products/{product_id}")
def get_product(product_id: str) -> dict:
    products = {p["product_id"]: p for p in db.get_products()}
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    p = products[product_id]

    metrics = [dict(m) for m in db.get_metrics_for_product(product_id)]

    signals = []
    for row in db.get_detected_signals(product_id):
        d = dict(row)
        d["evidence"] = json.loads(d["evidence"])
        signals.append(d)

    activity = read_decisions(product_name=p["name"], limit=50)

    return {
        "product_id": product_id,
        "name": p["name"],
        "category": p["category"],
        "base_price": p["base_price"],
        "planted_issue": _planted_issues().get(product_id),
        "metrics": metrics,
        "signals": signals,
        "activity": activity,
    }
