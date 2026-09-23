"""
generate_synthetic_data.py — builds a FAKE Amazon seller account: 14
products, 60 days of daily metrics each, with a KNOWN set of
deliberately PLANTED distress cases (inventory stockout, PPC waste,
rank/Buy Box drop) alongside healthy control products with no planted
issue.

This is the only place in the project that knows which cases were
planted on purpose — so it ALSO writes the ground-truth labels to
eval/labeled_set.json here, rather than leaving Phase 6 to guess which
products should be flagged after the fact. Anything the eval script
checks precision/recall against traces back to a label written by the
same code that generated the data.

Deterministic: seeded RNG, same dataset every run. Re-running this
script is a FULL regenerate — all three tables are wiped and rebuilt,
never an incremental append.

Planted patterns are deliberately made STRONGLY distinct from healthy
behavior (e.g. inventory forced to a low fixed starting point before
depleting, rather than a soft relative reduction) so they reliably
cross the signal detectors' thresholds regardless of upstream RNG
noise. Healthy control products are NOT guaranteed risk-free by
construction — a control product landing close to a threshold by
chance is a realistic false-positive risk, and Phase 6's eval is
supposed to measure that honestly, not have it engineered away here.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "db"))
import db  # noqa: E402

SEED = 42
NUM_DAYS = 60
EVAL_LABELS_PATH = Path(__file__).parent.parent / "eval" / "labeled_set.json"

# (product_id, name, category, base_price, planted_issue)
# planted_issue: None | "inventory_stockout" | "ppc_waste" | "rank_drop"
PRODUCT_PLAN = [
    ("P001", "Stainless Steel Garlic Press", "Kitchen", 14.99, "inventory_stockout"),
    ("P002", "Bamboo Cutting Board Set", "Kitchen", 29.99, "inventory_stockout"),
    ("P003", "Wireless Charging Pad", "Electronics", 19.99, "ppc_waste"),
    ("P004", "USB-C Hub 7-in-1", "Electronics", 34.99, "ppc_waste"),
    ("P005", "Silicone Ice Cube Trays", "Kitchen", 9.99, "rank_drop"),
    ("P006", "LED Desk Lamp", "Electronics", 24.99, "rank_drop"),
    ("P007", "Vitamin C Face Serum", "Beauty", 18.99, "inventory_stockout"),
    ("P008", "Bluetooth Earbuds Case", "Electronics", 12.99, "ppc_waste"),
    ("P009", "Ceramic Plant Pots (3-pack)", "Home & Garden", 22.99, "rank_drop"),
    ("P010", "Resistance Bands Set", "Sports", 15.99, None),
    ("P011", "Stainless Steel Water Bottle", "Sports", 21.99, None),
    ("P012", "Collagen Face Moisturizer", "Beauty", 26.99, None),
    ("P013", "Adjustable Yoga Mat", "Sports", 27.99, None),
    ("P014", "Solar Garden Lights (6-pack)", "Home & Garden", 31.99, None),
]


def _generate_healthy_series(rng: random.Random) -> list[dict]:
    rank = rng.randint(500, 3000)
    inventory = rng.randint(200, 500)
    days = []
    for _ in range(NUM_DAYS):
        units_sold = max(0, int(rng.gauss(8, 2)))
        if inventory < 100:
            inventory += 100
        inventory = max(0, inventory - units_sold)
        rank += rng.randint(-50, 50)
        rank = max(50, rank)
        ad_spend = round(rng.uniform(10, 30), 2)
        ad_clicks = rng.randint(20, 60)
        ad_sales = round(ad_spend * rng.uniform(3.0, 6.0), 2)  # healthy ACOS ~17-33%
        days.append(
            dict(
                units_sold=units_sold,
                inventory_level=inventory,
                rank=rank,
                has_buy_box=True,
                ad_spend=ad_spend,
                ad_clicks=ad_clicks,
                ad_sales=ad_sales,
            )
        )
    return days


def _generate_inventory_stockout_series(rng: random.Random) -> list[dict]:
    """Healthy for most of the window, then inventory is forced down
    from a deliberately low fixed starting point over the final 12
    days — guarantees this planted case actually crosses the
    detector's threshold, regardless of how the healthy phase's RNG
    happened to play out."""
    days = _generate_healthy_series(rng)
    inventory = 60  # deliberately low, independent of prior random walk
    for i in range(max(0, NUM_DAYS - 12), NUM_DAYS):
        units_sold = days[i]["units_sold"]
        inventory = max(0, inventory - units_sold)
        days[i]["inventory_level"] = inventory
    return days


def _generate_ppc_waste_series(rng: random.Random) -> list[dict]:
    """Healthy sales, but ad spend produces very little return for an
    extended recent stretch — sustained high ACOS."""
    days = _generate_healthy_series(rng)
    for i in range(max(0, NUM_DAYS - 20), NUM_DAYS):
        ad_spend = round(rng.uniform(35, 60), 2)
        ad_sales = round(ad_spend * rng.uniform(0.8, 1.3), 2)  # ACOS ~77-125%
        days[i]["ad_spend"] = ad_spend
        days[i]["ad_sales"] = ad_sales
        days[i]["ad_clicks"] = rng.randint(80, 150)
    return days


def _generate_rank_drop_series(rng: random.Random) -> list[dict]:
    """Rank worsens sharply over the back half of the window, and the
    Buy Box is lost for the final 8 days — two related signals checked
    independently, so either alone is enough to flag this case even if
    the other happens to fall short of its own threshold."""
    days = _generate_healthy_series(rng)
    start = max(0, NUM_DAYS - 18)
    current_rank = days[start]["rank"]
    for i in range(start, NUM_DAYS):
        current_rank += rng.randint(150, 400)
        days[i]["rank"] = current_rank
        if i >= NUM_DAYS - 8:
            days[i]["has_buy_box"] = False
    return days


_GENERATORS = {
    "inventory_stockout": _generate_inventory_stockout_series,
    "ppc_waste": _generate_ppc_waste_series,
    "rank_drop": _generate_rank_drop_series,
    None: _generate_healthy_series,
}


def generate() -> None:
    rng = random.Random(SEED)

    db.init_db()
    conn = db.get_connection()
    conn.execute("DELETE FROM daily_metrics")
    conn.execute("DELETE FROM products")
    conn.execute("DELETE FROM detected_signals")
    conn.commit()
    conn.close()

    start_date = date.today() - timedelta(days=NUM_DAYS)
    labels = []

    for product_id, name, category, base_price, planted_issue in PRODUCT_PLAN:
        db.insert_product(product_id, name, category, base_price)
        series = _GENERATORS[planted_issue](rng)

        for i, day_data in enumerate(series):
            metric_date = (start_date + timedelta(days=i)).isoformat()
            db.insert_daily_metric(product_id=product_id, date=metric_date, **day_data)

        labels.append(
            {"product_id": product_id, "name": name, "planted_issue": planted_issue}
        )

    EVAL_LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_LABELS_PATH.open("w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)

    planted_counts: dict[str | None, int] = {}
    for _, _, _, _, issue in PRODUCT_PLAN:
        planted_counts[issue] = planted_counts.get(issue, 0) + 1

    print(f"Generated {len(PRODUCT_PLAN)} products, {NUM_DAYS} days each.")
    print(f"Ground-truth labels written to {EVAL_LABELS_PATH}")
    print(f"Planted issue breakdown: {planted_counts}")

    from generate_intelligence_data import generate_intelligence_data

    generate_intelligence_data(PRODUCT_PLAN)


if __name__ == "__main__":
    generate()
