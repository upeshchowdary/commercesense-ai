"""
intelligence_db.py — CRUD for the four intelligence modules' tables
(listing_data/audits/recommendations, pricing_data/observations/analyses,
review_items/analyses, inventory_config, intelligence_runs). Same database
file, same get_connection() as db.py — this is organizational, not a
second database. Same style throughout: fresh connection per call, JSON
columns via json.dumps/loads.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from db import get_connection

# ---------------------------------------------------------------- Listing

def upsert_listing_data(
    product_id: str,
    title: str,
    brand: str,
    product_type: str,
    bullets: list[str],
    description: str,
    backend_keywords: str | None,
    attributes: dict[str, Any],
    image_urls: list[str],
    image_count: int,
    listing_status: str,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO listing_data
            (product_id, title, brand, product_type, bullets, description,
             backend_keywords, attributes, image_urls, image_count, listing_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id, title, brand, product_type, json.dumps(bullets), description,
            backend_keywords, json.dumps(attributes), json.dumps(image_urls),
            image_count, listing_status,
        ),
    )
    conn.commit()
    conn.close()


def get_listing_data(product_id: str) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM listing_data WHERE product_id = ?", (product_id,)).fetchone()
    conn.close()
    return row


def insert_listing_audit(
    product_id: str, score: int, category_scores: dict, failed_rules: list,
    warnings: list, passed_rules: list, analyzed_at: str,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO listing_audits
            (product_id, score, category_scores, failed_rules, warnings, passed_rules, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (product_id, score, json.dumps(category_scores), json.dumps(failed_rules),
         json.dumps(warnings), json.dumps(passed_rules), analyzed_at),
    )
    conn.commit()
    audit_id = cur.lastrowid
    conn.close()
    return audit_id


def get_latest_listing_audit(product_id: str) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM listing_audits WHERE product_id = ? ORDER BY analyzed_at DESC LIMIT 1",
        (product_id,),
    ).fetchone()
    conn.close()
    return row


def get_listing_audit_history(product_id: str) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM listing_audits WHERE product_id = ? ORDER BY analyzed_at DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    return rows


def insert_listing_recommendation(
    product_id: str, audit_id: int | None, field: str, current_value: str,
    proposed_value: str, changes: list[str], created_at: str,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO listing_recommendations
            (product_id, audit_id, field, current_value, proposed_value, changes, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """,
        (product_id, audit_id, field, current_value, proposed_value, json.dumps(changes), created_at),
    )
    conn.commit()
    rec_id = cur.lastrowid
    conn.close()
    return rec_id


def get_listing_recommendations(product_id: str) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM listing_recommendations WHERE product_id = ? ORDER BY created_at DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    return rows


def update_listing_recommendation_status(recommendation_id: int, status: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE listing_recommendations SET status = ? WHERE id = ?",
        (status, recommendation_id),
    )
    conn.commit()
    conn.close()


# ----------------------------------------------------------------- Pricing

def upsert_pricing_data(
    product_id: str, cogs: float, referral_fee_pct: float, fulfillment_fee: float,
    other_cost: float, target_margin_pct: float, currency: str = "USD",
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO pricing_data
            (product_id, cogs, referral_fee_pct, fulfillment_fee, other_cost, target_margin_pct, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (product_id, cogs, referral_fee_pct, fulfillment_fee, other_cost, target_margin_pct, currency),
    )
    conn.commit()
    conn.close()


def get_pricing_data(product_id: str) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM pricing_data WHERE product_id = ?", (product_id,)).fetchone()
    conn.close()
    return row


def insert_pricing_observation(
    product_id: str, competitor: str, price: float, currency: str, source: str,
    source_url: str | None, observed_at: str, confidence: str, is_verified: bool,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO pricing_observations
            (product_id, competitor, price, currency, source, source_url, observed_at, confidence, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (product_id, competitor, price, currency, source, source_url, observed_at,
         confidence, int(is_verified)),
    )
    conn.commit()
    conn.close()


def get_pricing_observations(product_id: str) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pricing_observations WHERE product_id = ? ORDER BY observed_at DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    return rows


def clear_pricing_observations_by_source(product_id: str, source: str) -> None:
    """Idempotent re-research: wipe only this source's prior observations
    (e.g. 'web') before inserting fresh ones, same pattern as
    signals.clear_detected_signals_by_type."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM pricing_observations WHERE product_id = ? AND source = ?",
        (product_id, source),
    )
    conn.commit()
    conn.close()


def insert_pricing_analysis(
    product_id: str, current_price: float, variable_cost: float, contribution: float,
    margin_pct: float, breakeven_price: float, target_margin_price: float,
    price_state: str, recommended_low: float | None, recommended_high: float | None,
    analyzed_at: str,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO pricing_analyses
            (product_id, current_price, variable_cost, contribution, margin_pct,
             breakeven_price, target_margin_price, price_state, recommended_low,
             recommended_high, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (product_id, current_price, variable_cost, contribution, margin_pct,
         breakeven_price, target_margin_price, price_state, recommended_low,
         recommended_high, analyzed_at),
    )
    conn.commit()
    analysis_id = cur.lastrowid
    conn.close()
    return analysis_id


def get_latest_pricing_analysis(product_id: str) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pricing_analyses WHERE product_id = ? ORDER BY analyzed_at DESC LIMIT 1",
        (product_id,),
    ).fetchone()
    conn.close()
    return row


def get_pricing_analysis_history(product_id: str) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pricing_analyses WHERE product_id = ? ORDER BY analyzed_at DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    return rows


# ------------------------------------------------------------------ Review

def insert_review_item(
    product_id: str, rating: int, review_text: str, review_date: str,
    verified_purchase: bool = True, source: str = "synthetic",
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO review_items (product_id, rating, review_text, review_date, verified_purchase, source)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (product_id, rating, review_text, review_date, int(verified_purchase), source),
    )
    conn.commit()
    conn.close()


def get_review_items(product_id: str) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM review_items WHERE product_id = ? ORDER BY review_date DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    return rows


def clear_review_items(product_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM review_items WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()


def insert_review_analysis(
    product_id: str, window_days: int, total_reviews: int, avg_rating: float,
    rating_distribution: dict, negative_pct: float, velocity: int, previous_velocity: int,
    trend: str, themes: list, emerging_issues: list, analyzed_at: str,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO review_analyses
            (product_id, window_days, total_reviews, avg_rating, rating_distribution,
             negative_pct, velocity, previous_velocity, trend, themes, emerging_issues, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (product_id, window_days, total_reviews, avg_rating, json.dumps(rating_distribution),
         negative_pct, velocity, previous_velocity, trend, json.dumps(themes),
         json.dumps(emerging_issues), analyzed_at),
    )
    conn.commit()
    analysis_id = cur.lastrowid
    conn.close()
    return analysis_id


def get_latest_review_analysis(product_id: str) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM review_analyses WHERE product_id = ? ORDER BY analyzed_at DESC LIMIT 1",
        (product_id,),
    ).fetchone()
    conn.close()
    return row


# --------------------------------------------------------------- Inventory

def upsert_inventory_config(
    product_id: str, lead_time_days: int, safety_days: int, moq: int | None,
    reorder_multiple: int | None, target_service_level: float = 0.95,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO inventory_config
            (product_id, lead_time_days, safety_days, moq, reorder_multiple, target_service_level)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (product_id, lead_time_days, safety_days, moq, reorder_multiple, target_service_level),
    )
    conn.commit()
    conn.close()


def get_inventory_config(product_id: str) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM inventory_config WHERE product_id = ?", (product_id,)).fetchone()
    conn.close()
    return row


# --------------------------------------------------------- Intelligence runs

def start_intelligence_run(run_id: str, product_id: str, module: str, provenance: str, started_at: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO intelligence_runs (run_id, product_id, module, status, provenance, started_at)
        VALUES (?, ?, ?, 'started', ?, ?)
        """,
        (run_id, product_id, module, provenance, started_at),
    )
    conn.commit()
    conn.close()


def complete_intelligence_run(run_id: str, status: str, completed_at: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE intelligence_runs SET status = ?, completed_at = ? WHERE run_id = ?",
        (status, completed_at, run_id),
    )
    conn.commit()
    conn.close()


def get_intelligence_runs(module: str | None = None, product_id: str | None = None, limit: int = 50) -> list[sqlite3.Row]:
    conn = get_connection()
    query = "SELECT * FROM intelligence_runs WHERE 1=1"
    params: list[Any] = []
    if module:
        query += " AND module = ?"
        params.append(module)
    if product_id:
        query += " AND product_id = ?"
        params.append(product_id)
    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_intelligence_run_stats(module: str) -> dict:
    """Observability counters for one intelligence module (spec §48),
    derived from the same intelligence_runs table every /analyze,
    /rewrite, /forecast, and /simulate call already writes to via
    RunTracker -- no second metrics mechanism. Duration is computed in
    Python (not SQL date math) because started_at/completed_at are
    ISO-8601 strings with timezone offsets."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, started_at, completed_at FROM intelligence_runs WHERE module = ?",
        (module,),
    ).fetchall()
    conn.close()

    run_count = len(rows)
    success_count = sum(1 for r in rows if r["status"] == "complete")
    failure_count = sum(1 for r in rows if r["status"] == "failed")
    in_progress_count = sum(1 for r in rows if r["status"] == "started")

    durations: list[float] = []
    for r in rows:
        if not r["completed_at"]:
            continue
        try:
            started = datetime.fromisoformat(r["started_at"])
            completed = datetime.fromisoformat(r["completed_at"])
            durations.append((completed - started).total_seconds())
        except ValueError:
            continue

    return {
        "run_count": run_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "in_progress_count": in_progress_count,
        "avg_duration_seconds": round(sum(durations) / len(durations), 3) if durations else None,
    }
