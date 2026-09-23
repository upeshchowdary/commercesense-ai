"""
run_eval.py — Phase 6: compares the ground-truth labels written by
data/generate_synthetic_data.py (eval/labeled_set.json) against
whatever is CURRENTLY in the detected_signals table.

This is deliberately a live comparison, not a cached/hardcoded
snapshot — if signal detection hasn't been (re)run since the last data
regenerate, that's reflected honestly in the result (see
`signals_have_been_run`), not papered over with stale numbers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "db"))
sys.path.insert(0, str(_PROJECT_ROOT / "data"))
import db  # noqa: E402
from generate_synthetic_data import SEED, NUM_DAYS  # noqa: E402

LABELED_SET_PATH = Path(__file__).parent / "labeled_set.json"

# planted_issue -> the signal_type a correct detector run should produce
_ISSUE_TO_SIGNAL_TYPE = {
    "inventory_stockout": "inventory_stockout",
    "ppc_waste": "ppc_waste",
    "rank_drop": "rank_drop",
}


def run_evaluation() -> dict:
    with LABELED_SET_PATH.open("r", encoding="utf-8") as f:
        labels: list[dict] = json.load(f)

    detected_rows = db.get_detected_signals()
    signals_have_been_run = len(detected_rows) > 0

    detected_by_product: dict[str, set[str]] = {}
    for row in detected_rows:
        detected_by_product.setdefault(row["product_id"], set()).add(row["signal_type"])

    results = []
    planted_count = 0
    detected_count = 0
    false_positive_count = 0

    for label in labels:
        product_id = label["product_id"]
        name = label["name"]
        planted_issue = label["planted_issue"]
        detected_types = detected_by_product.get(product_id, set())

        if planted_issue is None:
            # Healthy control: any detected signal at all is a false positive.
            is_false_positive = len(detected_types) > 0
            if is_false_positive:
                false_positive_count += 1
            results.append(
                {
                    "product_id": product_id,
                    "product": name,
                    "signal": None,
                    "expected": False,
                    "detected": len(detected_types) > 0,
                    "false_positive": is_false_positive,
                    "extra_signal_types": sorted(detected_types),
                    "result": "FAIL" if is_false_positive else "PASS",
                }
            )
        else:
            planted_count += 1
            expected_signal_type = _ISSUE_TO_SIGNAL_TYPE[planted_issue]
            was_detected = expected_signal_type in detected_types
            if was_detected:
                detected_count += 1
            # A planted product can ALSO trip an unrelated detector
            # (e.g. a stockout-planted product that also gets flagged
            # for rank_drop) — that extra, unrequested signal is a
            # false positive of its own and was previously never
            # counted, since only the expected signal was checked.
            extra_types = sorted(detected_types - {expected_signal_type})
            has_extra = len(extra_types) > 0
            if has_extra:
                false_positive_count += 1
            results.append(
                {
                    "product_id": product_id,
                    "product": name,
                    "signal": expected_signal_type,
                    "expected": True,
                    "detected": was_detected,
                    "false_positive": has_extra,
                    "extra_signal_types": extra_types,
                    "result": "PASS" if (was_detected and not has_extra) else "FAIL",
                }
            )

    return {
        "signals_have_been_run": signals_have_been_run,
        "products_tested": len(labels),
        "days_simulated": NUM_DAYS,
        "seed": SEED,
        "planted_cases": planted_count,
        "detected_cases": detected_count,
        "false_positives": false_positive_count,
        "results": results,
    }


if __name__ == "__main__":
    summary = run_evaluation()
    print(json.dumps(summary, indent=2))
