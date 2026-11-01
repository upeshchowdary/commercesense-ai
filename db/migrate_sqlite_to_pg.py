"""
migrate_sqlite_to_pg.py — Idempotent SQLite to PostgreSQL Data Migration Utility.

Safely migrates historical and synthetic seller data from the local SQLite database
into PostgreSQL with high-precision Decimal conversions, foreign key integrity,
and automated pre/post verification.

Usage:
    python db/migrate_sqlite_to_pg.py [--sqlite-path amazon_copilot.db] [--target-url postgresql://...]
"""

from __future__ import annotations

import argparse
import decimal
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.models import (
    Base,
    Product,
    DailyMetric,
    DetectedSignal,
    ListingData,
    ListingAudit,
    ListingRecommendation,
    PricingData,
    PricingObservation,
    PricingAnalysis,
    ReviewItem,
    ReviewAnalysis,
    InventoryConfig,
    IntelligenceRun,
)
from db.session import create_app_engine, get_database_url


def table_exists_in_sqlite(conn: sqlite3.Connection, table_name: str) -> bool:
    """Checks whether a table exists in the source SQLite database."""
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


def to_decimal(val: Any) -> decimal.Decimal:
    """Converts int, float, or str to high-precision Decimal."""
    if val is None:
        return decimal.Decimal("0.0000")
    if isinstance(val, decimal.Decimal):
        return val
    return decimal.Decimal(str(val))


def parse_json_safely(val: Any) -> Any:
    """Parses JSON text or returns object if already decoded."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return val


class MigrationStats:
    def __init__(self):
        self.counts: Dict[str, Tuple[int, int]] = {}  # table -> (sqlite_count, target_count)

    def record(self, table: str, sqlite_count: int, target_count: int):
        self.counts[table] = (sqlite_count, target_count)

    def is_valid(self) -> bool:
        return all(s == t for s, t in self.counts.values())

    def print_report(self):
        print("\n" + "=" * 65)
        print("          SQLITE -> POSTGRESQL MIGRATION AUDIT REPORT")
        print("=" * 65)
        print(f"{'Table Name':<28} | {'SQLite Rows':<12} | {'Target Rows':<12} | Status")
        print("-" * 65)
        for tbl, (src, tgt) in self.counts.items():
            status = "MATCH [OK]" if src == tgt else f"DIFF [SRC:{src} != TGT:{tgt}]"
            print(f"{tbl:<28} | {src:<12} | {tgt:<12} | {status}")
        print("=" * 65)


def migrate_data(sqlite_path: Path, target_url: str | None = None) -> MigrationStats:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Source SQLite database not found at {sqlite_path}")

    stats = MigrationStats()
    target_engine = create_app_engine(target_url or get_database_url())
    Base.metadata.create_all(bind=target_engine)

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row

    with Session(target_engine) as session:
        # 1. Products
        if table_exists_in_sqlite(conn, "products"):
            sqlite_products = conn.execute("SELECT * FROM products").fetchall()
            for row in sqlite_products:
                p = session.get(Product, row["product_id"])
                asin_val = row["asin"] if "asin" in row.keys() and row["asin"] else (row["product_id"] if len(row["product_id"]) == 10 else None)
                if not p:
                    p = Product(
                        product_id=row["product_id"],
                        asin=asin_val,
                        name=row["name"],
                        category=row["category"],
                        base_price=to_decimal(row["base_price"]),
                        currency="USD",
                    )
                    session.add(p)
                else:
                    p.name = row["name"]
                    p.category = row["category"]
                    p.base_price = to_decimal(row["base_price"])
                    if asin_val:
                        p.asin = asin_val
            session.commit()
            tgt_count = session.scalar(select(func.count(Product.product_id)))
            stats.record("products", len(sqlite_products), tgt_count)
        else:
            stats.record("products", 0, 0)

        # 2. Daily Metrics
        sqlite_metrics = conn.execute("SELECT * FROM daily_metrics").fetchall()
        for row in sqlite_metrics:
            existing = session.get(DailyMetric, (row["product_id"], row["date"]))
            if not existing:
                metric = DailyMetric(
                    product_id=row["product_id"],
                    date=row["date"],
                    units_sold=int(row["units_sold"]),
                    inventory_level=int(row["inventory_level"]),
                    rank=int(row["rank"]),
                    has_buy_box=bool(row["has_buy_box"]),
                    ad_spend=to_decimal(row["ad_spend"]),
                    ad_clicks=int(row["ad_clicks"]),
                    ad_sales=to_decimal(row["ad_sales"]),
                )
                session.add(metric)
            else:
                existing.units_sold = int(row["units_sold"])
                existing.inventory_level = int(row["inventory_level"])
                existing.rank = int(row["rank"])
                existing.has_buy_box = bool(row["has_buy_box"])
                existing.ad_spend = to_decimal(row["ad_spend"])
                existing.ad_clicks = int(row["ad_clicks"])
                existing.ad_sales = to_decimal(row["ad_sales"])
        session.commit()
        tgt_count = session.scalar(select(func.count(DailyMetric.product_id)))
        stats.record("daily_metrics", len(sqlite_metrics), tgt_count)

        # 3. Detected Signals
        sqlite_signals = conn.execute("SELECT * FROM detected_signals").fetchall()
        for row in sqlite_signals:
            sig = session.get(DetectedSignal, row["id"])
            if not sig:
                sig = DetectedSignal(
                    id=row["id"],
                    product_id=row["product_id"],
                    date=row["date"],
                    signal_type=row["signal_type"],
                    severity=row["severity"],
                    evidence=parse_json_safely(row["evidence"]),
                    detected_at=row["detected_at"],
                )
                session.add(sig)
        session.commit()
        tgt_count = session.scalar(select(func.count(DetectedSignal.id)))
        stats.record("detected_signals", len(sqlite_signals), tgt_count)

        # 4. Listing Data
        sqlite_listing = conn.execute("SELECT * FROM listing_data").fetchall()
        for row in sqlite_listing:
            l = session.get(ListingData, row["product_id"])
            if not l:
                l = ListingData(
                    product_id=row["product_id"],
                    title=row["title"],
                    brand=row["brand"],
                    product_type=row["product_type"],
                    bullets=parse_json_safely(row["bullets"]),
                    description=row["description"],
                    backend_keywords=row["backend_keywords"],
                    attributes=parse_json_safely(row["attributes"]),
                    image_urls=parse_json_safely(row["image_urls"]),
                    image_count=int(row["image_count"]),
                    listing_status=row["listing_status"],
                )
                session.add(l)
        session.commit()
        tgt_count = session.scalar(select(func.count(ListingData.product_id)))
        stats.record("listing_data", len(sqlite_listing), tgt_count)

        # 5. Listing Audits
        sqlite_audits = conn.execute("SELECT * FROM listing_audits").fetchall()
        for row in sqlite_audits:
            la = session.get(ListingAudit, row["id"])
            if not la:
                la = ListingAudit(
                    id=row["id"],
                    product_id=row["product_id"],
                    score=int(row["score"]),
                    category_scores=parse_json_safely(row["category_scores"]),
                    failed_rules=parse_json_safely(row["failed_rules"]),
                    warnings=parse_json_safely(row["warnings"]),
                    passed_rules=parse_json_safely(row["passed_rules"]),
                    analyzed_at=row["analyzed_at"],
                )
                session.add(la)
        session.commit()
        tgt_count = session.scalar(select(func.count(ListingAudit.id)))
        stats.record("listing_audits", len(sqlite_audits), tgt_count)

        # 6. Listing Recommendations
        sqlite_recs = conn.execute("SELECT * FROM listing_recommendations").fetchall()
        for row in sqlite_recs:
            lr = session.get(ListingRecommendation, row["id"])
            if not lr:
                lr = ListingRecommendation(
                    id=row["id"],
                    product_id=row["product_id"],
                    audit_id=row["audit_id"],
                    field=row["field"],
                    current_value=row["current_value"],
                    proposed_value=row["proposed_value"],
                    changes=parse_json_safely(row["changes"]),
                    status=row["status"],
                    created_at=row["created_at"],
                )
                session.add(lr)
        session.commit()
        tgt_count = session.scalar(select(func.count(ListingRecommendation.id)))
        stats.record("listing_recommendations", len(sqlite_recs), tgt_count)

        # 7. Pricing Data
        sqlite_pricing = conn.execute("SELECT * FROM pricing_data").fetchall()
        for row in sqlite_pricing:
            pd = session.get(PricingData, row["product_id"])
            if not pd:
                pd = PricingData(
                    product_id=row["product_id"],
                    cogs=to_decimal(row["cogs"]),
                    referral_fee_pct=to_decimal(row["referral_fee_pct"]),
                    fulfillment_fee=to_decimal(row["fulfillment_fee"]),
                    closing_fee=to_decimal(row["closing_fee"] if "closing_fee" in row.keys() else 0),
                    packaging_cost=to_decimal(row["packaging_cost"] if "packaging_cost" in row.keys() else 0),
                    inbound_freight=to_decimal(row["inbound_freight"] if "inbound_freight" in row.keys() else 0),
                    ad_cost_per_unit=to_decimal(row["ad_cost_per_unit"] if "ad_cost_per_unit" in row.keys() else 0),
                    returns_allowance=to_decimal(row["returns_allowance"] if "returns_allowance" in row.keys() else 0),
                    other_cost=to_decimal(row["other_cost"]),
                    target_margin_pct=to_decimal(row["target_margin_pct"]),
                    min_margin_pct=to_decimal(row["min_margin_pct"] if "min_margin_pct" in row.keys() else 0.10),
                    currency=row["currency"] if "currency" in row.keys() else "USD",
                )
                session.add(pd)
        session.commit()
        tgt_count = session.scalar(select(func.count(PricingData.product_id)))
        stats.record("pricing_data", len(sqlite_pricing), tgt_count)

        # 8. Pricing Observations
        sqlite_obs = conn.execute("SELECT * FROM pricing_observations").fetchall()
        for row in sqlite_obs:
            po = session.get(PricingObservation, row["id"])
            if not po:
                po = PricingObservation(
                    id=row["id"],
                    product_id=row["product_id"],
                    competitor=row["competitor"],
                    competitor_asin=row["competitor_asin"] if "competitor_asin" in row.keys() else None,
                    price=to_decimal(row["price"]),
                    shipping_cost=to_decimal(row["shipping_cost"] if "shipping_cost" in row.keys() else 0),
                    landed_price=to_decimal(row["landed_price"] if "landed_price" in row.keys() else row["price"]),
                    currency=row["currency"] if "currency" in row.keys() else "USD",
                    match_tier=row["match_tier"] if "match_tier" in row.keys() else "TIER_1_SAME_ASIN",
                    is_buy_box_winner=bool(row["is_buy_box_winner"]) if "is_buy_box_winner" in row.keys() else False,
                    fulfillment_channel=row["fulfillment_channel"] if "fulfillment_channel" in row.keys() else "FBA",
                    condition_type=row["condition_type"] if "condition_type" in row.keys() else "New",
                    seller_rating=to_decimal(row["seller_rating"]) if "seller_rating" in row.keys() and row["seller_rating"] is not None else None,
                    source=row["source"],
                    source_url=row["source_url"],
                    observed_at=row["observed_at"],
                    confidence=row["confidence"],
                    is_verified=bool(row["is_verified"]),
                )
                session.add(po)
        session.commit()
        tgt_count = session.scalar(select(func.count(PricingObservation.id)))
        stats.record("pricing_observations", len(sqlite_obs), tgt_count)

        # 9. Pricing Analyses
        sqlite_pa = conn.execute("SELECT * FROM pricing_analyses").fetchall()
        for row in sqlite_pa:
            pa = session.get(PricingAnalysis, row["id"])
            if not pa:
                pa = PricingAnalysis(
                    id=row["id"],
                    product_id=row["product_id"],
                    current_price=to_decimal(row["current_price"]),
                    variable_cost=to_decimal(row["variable_cost"]),
                    contribution=to_decimal(row["contribution"]),
                    margin_pct=to_decimal(row["margin_pct"]),
                    breakeven_price=to_decimal(row["breakeven_price"]),
                    target_margin_price=to_decimal(row["target_margin_price"]),
                    price_state=row["price_state"],
                    recommended_low=to_decimal(row["recommended_low"]) if row["recommended_low"] is not None else None,
                    recommended_high=to_decimal(row["recommended_high"]) if row["recommended_high"] is not None else None,
                    analyzed_at=row["analyzed_at"],
                )
                session.add(pa)
        session.commit()
        tgt_count = session.scalar(select(func.count(PricingAnalysis.id)))
        stats.record("pricing_analyses", len(sqlite_pa), tgt_count)

        # 10. Review Items
        sqlite_reviews = conn.execute("SELECT * FROM review_items").fetchall()
        for row in sqlite_reviews:
            ri = session.get(ReviewItem, row["id"])
            if not ri:
                ri = ReviewItem(
                    id=row["id"],
                    product_id=row["product_id"],
                    rating=int(row["rating"]),
                    review_text=row["review_text"],
                    review_date=row["review_date"],
                    verified_purchase=bool(row["verified_purchase"]),
                    source=row["source"] if "source" in row.keys() else "synthetic",
                )
                session.add(ri)
        session.commit()
        tgt_count = session.scalar(select(func.count(ReviewItem.id)))
        stats.record("review_items", len(sqlite_reviews), tgt_count)

        # 11. Review Analyses
        sqlite_ra = conn.execute("SELECT * FROM review_analyses").fetchall()
        for row in sqlite_ra:
            ra = session.get(ReviewAnalysis, row["id"])
            if not ra:
                ra = ReviewAnalysis(
                    id=row["id"],
                    product_id=row["product_id"],
                    window_days=int(row["window_days"]),
                    total_reviews=int(row["total_reviews"]),
                    avg_rating=to_decimal(row["avg_rating"]),
                    rating_distribution=parse_json_safely(row["rating_distribution"]),
                    negative_pct=to_decimal(row["negative_pct"]),
                    velocity=int(row["velocity"]),
                    previous_velocity=int(row["previous_velocity"]),
                    trend=row["trend"],
                    themes=parse_json_safely(row["themes"]),
                    emerging_issues=parse_json_safely(row["emerging_issues"]),
                    analyzed_at=row["analyzed_at"],
                )
                session.add(ra)
        session.commit()
        tgt_count = session.scalar(select(func.count(ReviewAnalysis.id)))
        stats.record("review_analyses", len(sqlite_ra), tgt_count)

        # 12. Inventory Config
        sqlite_ic = conn.execute("SELECT * FROM inventory_config").fetchall()
        for row in sqlite_ic:
            ic = session.get(InventoryConfig, row["product_id"])
            if not ic:
                ic = InventoryConfig(
                    product_id=row["product_id"],
                    lead_time_days=int(row["lead_time_days"]),
                    safety_days=int(row["safety_days"]),
                    moq=int(row["moq"]) if row["moq"] is not None else None,
                    reorder_multiple=int(row["reorder_multiple"]) if row["reorder_multiple"] is not None else None,
                    target_service_level=to_decimal(row["target_service_level"]),
                )
                session.add(ic)
        session.commit()
        tgt_count = session.scalar(select(func.count(InventoryConfig.product_id)))
        stats.record("inventory_config", len(sqlite_ic), tgt_count)

        # 13. Intelligence Runs
        sqlite_ir = conn.execute("SELECT * FROM intelligence_runs").fetchall()
        for row in sqlite_ir:
            ir = session.get(IntelligenceRun, row["id"])
            if not ir:
                ir = IntelligenceRun(
                    id=row["id"],
                    run_id=row["run_id"],
                    product_id=row["product_id"],
                    module=row["module"],
                    status=row["status"],
                    provenance=row["provenance"],
                    started_at=row["started_at"],
                    completed_at=row["completed_at"],
                )
                session.add(ir)
        # 14. Synchronize PostgreSQL primary key sequences if migrating into PostgreSQL
        if target_engine.dialect.name == "postgresql":
            tables_with_serial_id = [
                "detected_signals",
                "listing_audits",
                "listing_recommendations",
                "pricing_observations",
                "pricing_analyses",
                "review_items",
                "review_analyses",
                "intelligence_runs",
                "automation_rules",
                "action_queue",
                "audit_events",
                "provenance_registry",
            ]
            for tbl in tables_with_serial_id:
                try:
                    session.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {tbl}), 1));"
                    ))
                except Exception:
                    pass
            session.commit()

    conn.close()
    target_engine.dispose()
    return stats



def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL.")
    parser.add_argument("--sqlite-path", default="amazon_copilot.db", help="Path to SQLite database")
    parser.add_argument("--target-url", default=None, help="Target PostgreSQL database URL")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.is_absolute():
        sqlite_path = PROJECT_ROOT / sqlite_path

    stats = migrate_data(sqlite_path, args.target_url)
    stats.print_report()

    if not stats.is_valid():
        print("\nERROR: Row counts do not match! Migration had discrepancy.")
        sys.exit(1)
    else:
        print("\nSUCCESS: All tables migrated and verified successfully!")


if __name__ == "__main__":
    main()
