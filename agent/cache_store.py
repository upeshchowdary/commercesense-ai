"""
cache_store.py  a small SQLite cache so the same product isn't
re-searched on the live web every time the demo button is clicked.
This is the MinIO-equivalent for this project, at zero extra
infrastructure: one table, one TTL check.

Caching here is a correctness/cost decision, not just a nice-to-have:
without it, hitting "refresh" twice in front of judges burns search
quota and risks a different (and possibly worse) answer the second
time, for no reason.

Cache keys are normalized (trimmed + lowercased + whitespace-collapsed)
so "Bose QuietComfort Ultra headphones" and "bose quietcomfort ultra
headphones" hit the same cache entry instead of silently triggering
two separate live runs. The ORIGINAL casing is still preserved inside
the stored bundle itself  normalization only affects the lookup key.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from schema import ResearchBundle

DB_PATH = Path(os.environ.get("CACHE_DB_PATH", "research_cache.db"))


def _normalize_key(product_name: str) -> str:
    return " ".join(product_name.strip().lower().split())


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_cache (
            product_name TEXT PRIMARY KEY,
            bundle_json   TEXT NOT NULL,
            cached_at     TEXT NOT NULL
        )
        """
    )
    return conn


def get_cached_bundle(product_name: str, ttl_hours: int) -> ResearchBundle | None:
    """Return a cached bundle if one exists and is still fresh, else None."""
    key = _normalize_key(product_name)
    conn = _get_conn()
    row = conn.execute(
        "SELECT bundle_json, cached_at FROM research_cache WHERE product_name = ?",
        (key,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    bundle_json, cached_at = row
    cached_time = datetime.fromisoformat(cached_at)
    if datetime.now(timezone.utc) - cached_time > timedelta(hours=ttl_hours):
        return None  # stale  treat exactly like a cache miss

    return ResearchBundle(**json.loads(bundle_json))


def save_bundle_to_cache(bundle: ResearchBundle) -> None:
    key = _normalize_key(bundle.product_name)
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO research_cache (product_name, bundle_json, cached_at)
        VALUES (?, ?, ?)
        ON CONFLICT(product_name) DO UPDATE SET
            bundle_json = excluded.bundle_json,
            cached_at   = excluded.cached_at
        """,
        (
            key,
            bundle.model_dump_json(),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
