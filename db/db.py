"""
db.py — thin SQLite helper for the synthetic seller-account data. This
is a completely SEPARATE database from research_cache.db (Agent 5's
live-search cache) — this one holds FAKE product/metrics/signal data,
that one holds real cached web-search bundles. Never mix them; this is
the enforced boundary between the project's two halves.

Path resolution deliberately mirrors the fix applied to
decision_log.py / cache_store.py: anchored to project root, not CWD,
so this behaves correctly whether run from db/, signals/, or the
project root.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
PROJECT_ROOT = Path(__file__).parent.parent
_env_db_path = os.environ.get("SQLITE_DB_PATH", "amazon_copilot.db")
_db_path_obj = Path(_env_db_path)
DB_PATH = _db_path_obj if _db_path_obj.is_absolute() else (PROJECT_ROOT / _db_path_obj)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they don't exist. Safe to call every time
    — CREATE TABLE IF NOT EXISTS throughout."""
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def insert_product(product_id: str, name: str, category: str, base_price: float) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO products (product_id, name, category, base_price) VALUES (?, ?, ?, ?)",
        (product_id, name, category, base_price),
    )
    conn.commit()
    conn.close()


def insert_daily_metric(
    product_id: str,
    date: str,
    units_sold: int,
    inventory_level: int,
    rank: int,
    has_buy_box: bool,
    ad_spend: float,
    ad_clicks: int,
    ad_sales: float,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO daily_metrics
            (product_id, date, units_sold, inventory_level, rank, has_buy_box, ad_spend, ad_clicks, ad_sales)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (product_id, date, units_sold, inventory_level, rank, int(has_buy_box), ad_spend, ad_clicks, ad_sales),
    )
    conn.commit()
    conn.close()


def insert_detected_signal(
    product_id: str, date: str, signal_type: str, severity: str, evidence: dict, detected_at: str
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO detected_signals (product_id, date, signal_type, severity, evidence, detected_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (product_id, date, signal_type, severity, json.dumps(evidence), detected_at),
    )
    conn.commit()
    conn.close()


def get_products() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY product_id").fetchall()
    conn.close()
    return rows


def get_metrics_for_product(product_id: str) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM daily_metrics WHERE product_id = ? ORDER BY date",
        (product_id,),
    ).fetchall()
    conn.close()
    return rows


def get_detected_signals(product_id: str | None = None) -> list[sqlite3.Row]:
    conn = get_connection()
    if product_id:
        rows = conn.execute(
            "SELECT * FROM detected_signals WHERE product_id = ? ORDER BY date DESC",
            (product_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM detected_signals ORDER BY date DESC").fetchall()
    conn.close()
    return rows


def clear_detected_signals() -> None:
    """Wipe detected_signals so signal detectors can be re-run cleanly
    without accumulating duplicate rows across repeated demo runs."""
    conn = get_connection()
    conn.execute("DELETE FROM detected_signals")
    conn.commit()
    conn.close()
