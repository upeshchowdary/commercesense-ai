"""
db package for CommerceSense AI.
Re-exports the core SQLite helpers from db.py for backward compatibility with existing code.
"""

from db.db import (
    DB_PATH,
    SCHEMA_PATH,
    clear_detected_signals,
    clear_detected_signals_by_type,
    get_connection,
    get_detected_signals,
    get_metrics_for_product,
    get_products,
    init_db,
    insert_daily_metric,
    insert_detected_signal,
    insert_product,
)

__all__ = [
    "DB_PATH",
    "SCHEMA_PATH",
    "clear_detected_signals",
    "clear_detected_signals_by_type",
    "get_connection",
    "get_detected_signals",
    "get_metrics_for_product",
    "get_products",
    "init_db",
    "insert_daily_metric",
    "insert_detected_signal",
    "insert_product",
]
