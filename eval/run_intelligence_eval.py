"""
run_intelligence_eval.py — Phase 6 extension: live comparison of the
listing/pricing/review ground truth (eval/labeled_set_intelligence.json,
written by data/generate_intelligence_data.py) against what the engines
actually detect right now. Same "live, never hardcoded" philosophy as
eval/run_eval.py — classification metrics only (TP/FP/TN/FN, precision/
recall/F1), clearly separate from any forecast-error metric.

Inventory Intelligence isn't included here: its outputs (days of cover,
reorder point, etc.) are a forecast, not a planted true/false label, so it
doesn't fit a TP/FP/TN/FN table the way the other three do.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("db", "intelligence"):
    _p = str(_PROJECT_ROOT / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import db  # noqa: E402
import intelligence_db as idb  # noqa: E402
from listing_engine import evaluate_listing, score_listing  # noqa: E402
from pricing_engine import classify_price_state, contribution_margin, price_distribution  # noqa: E402
from review_engine import detect_emerging_issues, discover_candidate_words, themes_for_category  # noqa: E402

LABELS_PATH = Path(__file__).parent / "labeled_set_intelligence.json"


def _prf1(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if (precision and recall and (precision + recall)) else None
    return {
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
    }


def _record(result_list: list, count_dict: dict, product_id: str, name: str, expected: bool, detected: bool | None) -> None:
    if detected is None:
        result = "NO_DATA"
    elif expected and detected:
        result, key = "TP", "tp"
        count_dict[key] += 1
    elif expected and not detected:
        result, key = "FN", "fn"
        count_dict[key] += 1
    elif not expected and detected:
        result, key = "FP", "fp"
        count_dict[key] += 1
    else:
        result, key = "TN", "tn"
        count_dict[key] += 1
    result_list.append({"product_id": product_id, "product": name, "expected": expected, "detected": detected, "result": result})


def run_intelligence_evaluation() -> dict:
    if not LABELS_PATH.exists():
        return {"data_available": False, "message": "No intelligence ground truth found — run data/generate_synthetic_data.py first."}

    with LABELS_PATH.open("r", encoding="utf-8") as f:
        labels = json.load(f)

    products = {p["product_id"]: p for p in db.get_products()}
    results: dict[str, list] = {"listing": [], "pricing": [], "review": []}
    counts = {m: {"tp": 0, "fp": 0, "tn": 0, "fn": 0} for m in results}

    for label in labels:
        pid = label["product_id"]
        product = products.get(pid)
        if product is None:
            continue

        # --- Listing: expected "poor" -> detected via score < 70 ---
        listing_row = idb.get_listing_data(pid)
        detected_poor = None
        if listing_row:
            d = dict(listing_row)
            rules = evaluate_listing(
                title=d["title"], brand=d["brand"], product_type=d["product_type"],
                bullets=json.loads(d["bullets"]), description=d["description"],
                attributes=json.loads(d["attributes"]), image_count=d["image_count"],
                image_urls=json.loads(d["image_urls"]),
            )
            detected_poor = score_listing(rules)["score"] < 70
        _record(results["listing"], counts["listing"], pid, label["name"], label["poor_listing"], detected_poor)

        # --- Pricing: expected "below margin floor" ---
        pricing_row = idb.get_pricing_data(pid)
        detected_below = None
        if pricing_row:
            cm = contribution_margin(
                product["base_price"], pricing_row["cogs"], pricing_row["referral_fee_pct"],
                pricing_row["fulfillment_fee"], pricing_row["other_cost"],
            )
            obs = [o["price"] for o in idb.get_pricing_observations(pid)]
            dist = price_distribution(obs, product["base_price"])
            state = classify_price_state(cm["margin_pct"], pricing_row["target_margin_pct"], product["base_price"], dist["median"])
            detected_below = state == "BELOW_MARGIN_FLOOR"
        _record(results["pricing"], counts["pricing"], pid, label["name"], label["below_margin_floor"], detected_below)

        # --- Review: expected an emerging issue ---
        reviews = [dict(r) for r in idb.get_review_items(pid)]
        expected_theme = label["emerging_review_issue"]
        expected_emerging = expected_theme is not None
        detected_emerging = None
        if reviews:
            candidate_themes = set(themes_for_category(product["category"]) + discover_candidate_words(reviews, top_n=6))
            if expected_theme:
                candidate_themes.add(expected_theme)
            detected_emerging = any(detect_emerging_issues(reviews, t) for t in candidate_themes)
        _record(results["review"], counts["review"], pid, label["name"], expected_emerging, detected_emerging)

    summary = {
        module: {**counts[module], **_prf1(counts[module]["tp"], counts[module]["fp"], counts[module]["fn"])}
        for module in counts
    }
    return {"data_available": True, "results": results, "summary": summary}


if __name__ == "__main__":
    print(json.dumps(run_intelligence_evaluation(), indent=2))
