"""
test_db_models.py — Tests for SQLAlchemy 2.0 relational models and SQLite migration utility.
"""

from __future__ import annotations

import decimal
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from db.models import (
    Base,
    Product,
    DailyMetric,
    DetectedSignal,
    ListingData,
    PricingData,
    ReviewItem,
    InventoryConfig,
    ProvenanceRegistryRecord,
)
from db.migrate_sqlite_to_pg import migrate_data, to_decimal
from db.session import create_app_engine, init_db_schema


def test_to_decimal_precision():
    """Verifies that to_decimal preserves exact numeric values without float imprecision."""
    d1 = to_decimal(49.99)
    assert isinstance(d1, decimal.Decimal)
    assert d1 == decimal.Decimal("49.99")

    d2 = to_decimal("1299.5000")
    assert d2 == decimal.Decimal("1299.5000")

    d3 = to_decimal(None)
    assert d3 == decimal.Decimal("0.0000")


def test_sqlite_to_pg_migration_utility():
    """Tests the idempotent migration utility migrating existing SQLite data into target store."""
    src_db = Path("amazon_copilot.db")
    if not src_db.exists():
        pytest.skip("amazon_copilot.db not found for migration test")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_target_path = Path(tmp_file.name)

    try:
        target_url = f"sqlite:///{tmp_target_path.as_posix()}"
        stats = migrate_data(src_db, target_url=target_url)

        assert stats.is_valid(), f"Migration stats mismatch: {stats.counts}"
        assert stats.counts["products"][0] == 14
        assert stats.counts["products"][1] == 14
        assert stats.counts["daily_metrics"][0] == 840
        assert stats.counts["daily_metrics"][1] == 840
        assert stats.counts["pricing_data"][0] == 14
        assert stats.counts["pricing_data"][1] == 14

        # Verify idempotency by running migration a second time
        stats2 = migrate_data(src_db, target_url=target_url)
        assert stats2.is_valid()
        assert stats2.counts["products"][1] == 14
        assert stats2.counts["daily_metrics"][1] == 840

        # Verify decimal types in migrated target database
        target_engine = create_app_engine(target_url)
        try:
            with Session(target_engine) as session:
                p1 = session.get(Product, "P001")
                assert p1 is not None
                assert isinstance(p1.base_price, decimal.Decimal)
                assert p1.base_price > 0

                pricing1 = session.get(PricingData, "P001")
                assert pricing1 is not None
                assert isinstance(pricing1.cogs, decimal.Decimal)
                assert isinstance(pricing1.referral_fee_pct, decimal.Decimal)
        finally:
            target_engine.dispose()

    finally:
        if tmp_target_path.exists():
            try:
                tmp_target_path.unlink()
            except OSError:
                pass



def test_schema_creation_and_provenance_record():
    """Verifies table schema generation and provenance registry insertion."""
    engine = create_engine("sqlite:///:memory:", future=True)
    init_db_schema(engine)

    with Session(engine) as session:
        rec = ProvenanceRegistryRecord(
            source_id="amzn-sp-api",
            provider="amzn-sp-api",
            source_type="AMAZON_OFFICIAL",
            marketplace_id="A21TJRUUN4KGV",
            currency="INR",
            confidence="high",
            limitations=["Delayed up to 15m"],
        )
        session.add(rec)
        session.commit()

        queried = session.scalar(select(ProvenanceRegistryRecord).where(ProvenanceRegistryRecord.source_id == "amzn-sp-api"))
        assert queried is not None
        assert queried.provider == "amzn-sp-api"
        assert queried.limitations == ["Delayed up to 15m"]


def test_all_17_tables_present_in_metadata():
    """Confirms all 17 required relational tables are defined in SQLAlchemy Base.metadata."""
    expected_tables = {
        "products",
        "daily_metrics",
        "detected_signals",
        "listing_data",
        "listing_audits",
        "listing_recommendations",
        "pricing_data",
        "pricing_observations",
        "pricing_analyses",
        "review_items",
        "review_analyses",
        "inventory_config",
        "intelligence_runs",
        "automation_rules",
        "action_queue",
        "audit_events",
        "provenance_registry",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables)
    assert len(expected_tables) == 17
