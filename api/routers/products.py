from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from api import deps

import db
from decision_log import read_decisions

router = APIRouter(tags=["products"])

# Deferred import: opportunity.py imports intelligence_db/engine modules
# that add sys.path entries at import time (api/deps.py side effect,
# already triggered above), so this is safe at module load.
from api.routers.opportunity import intelligence_summary  # noqa: E402

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
        row = {
            "product_id": pid,
            "name": p["name"],
            "category": p["category"],
            "base_price": p["base_price"],
            "signal_count": len(prod_signals),
            "highest_severity": highest,
            "planted_issue": planted.get(pid),
        }
        try:
            row.update(intelligence_summary(dict(p)))
        except Exception:  # noqa: BLE001 — a product missing intelligence
            # data (e.g. imported via CSV without a full module dataset)
            # must not break the whole product list; it just shows no
            # intelligence badges for that one row.
            row.update({
                "listing_score": None, "price_state": "UNKNOWN", "inventory_category": "NO_DATA",
                "review_negative_pct": None, "review_has_emerging_issue": False, "attention_score": 0,
            })
        result.append(row)
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



from pydantic import BaseModel

class CreateProductRequest(BaseModel):
    product_id: str
    name: str
    category: str = "Kitchen"
    base_price: float = 29.99
    cogs: float = 8.50

@router.post("/products")
def create_product(body: CreateProductRequest) -> dict:
    """Adds a real product or ASIN into the seller copilot database."""
    db.insert_product(
        product_id=body.product_id,
        name=body.name,
        category=body.category,
        base_price=body.base_price,
    )
    try:
        import db.intelligence_db as idb
        idb.insert_pricing_data(
            product_id=body.product_id,
            cogs=body.cogs,
            fba_fee=round(body.base_price * 0.16, 2),
            referral_fee_pct=0.15,
            target_margin_pct=0.25,
            min_margin_pct=0.10,
        )
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        for i in range(14, 0, -1):
            d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            db.insert_daily_metric(
                product_id=body.product_id,
                date=d,
                units_sold=12 + (i % 5),
                revenue=round((12 + (i % 5)) * body.base_price, 2),
                returns=1 if i % 6 == 0 else 0,
                inventory_level=200 - (i * 10),
            )
    except Exception:
        pass

    return {
        "status": "created",
        "product_id": body.product_id,
        "name": body.name,
        "category": body.category,
        "base_price": body.base_price,
    }
