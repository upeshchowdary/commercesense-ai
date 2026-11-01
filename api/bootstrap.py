"""
bootstrap.py — first-boot data seeding for serverless deployments.

On Vercel every cold-started instance gets an empty /tmp (see deps.py
for the path redirection), so there is no synthetic seller-account
database to read. This seeds one by calling the SAME deterministic
generators (SEED=42) and the SAME three signal detectors used locally —
no second copy of any data or detection logic lives here.

Runs only when deps.is_serverless() is true and the products table is
empty, so local development (with its existing amazon_copilot.db) is
never touched. Ground-truth label files are redirected to /tmp because
the deployed eval/ directory is read-only; the committed
eval/labeled_set*.json files are byte-for-byte what the generators
produce, so the evaluator still reads the correct ground truth.
"""

from __future__ import annotations

import logging

from api import deps

logger = logging.getLogger("seller_copilot.bootstrap")

_state: dict = {"seeded": False, "error": None}


def seed_status() -> dict:
    return dict(_state)


def _products_count() -> int:
    import db

    conn = db.get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    finally:
        conn.close()


def seed_if_empty() -> None:
    if not deps.is_serverless():
        return
    try:
        import db
        from db.session import init_db_schema

        db.init_db()
        init_db_schema()
        if _products_count() > 0:
            _state["seeded"] = True
            return

        import generate_intelligence_data
        import generate_synthetic_data

        generate_synthetic_data.EVAL_LABELS_PATH = deps.SERVERLESS_TMP / "labeled_set.json"
        generate_intelligence_data.EVAL_LABELS_PATH = (
            deps.SERVERLESS_TMP / "labeled_set_intelligence.json"
        )
        generate_synthetic_data.generate()

        from inventory_signal import run_inventory_signal_for_all_products
        from ppc_waste_signal import run_ppc_waste_signal_for_all_products
        from rank_bb_signal import run_rank_bb_signal_for_all_products

        run_inventory_signal_for_all_products()
        run_ppc_waste_signal_for_all_products()
        run_rank_bb_signal_for_all_products()
        _state["seeded"] = True
    except Exception as exc:  # noqa: BLE001 — never take the whole API down
        logger.exception("Serverless data seeding failed")
        _state["error"] = f"{type(exc).__name__}: {exc}"
