"""
models.py — SQLAlchemy 2.0 Relational Data Models for CommerceSense AI v3.

Defines the PostgreSQL schema mirroring catalog master, daily time-series metrics,
intelligence audits/recommendations, cost accounting, actions, and provenance.
Compatible with PostgreSQL 16+ and SQLite fallback.
"""

from __future__ import annotations

import decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator


# Type helper for JSON columns across both PostgreSQL and SQLite
class UniversalJSON(TypeDecorator):
    """Uses native JSONB on PostgreSQL and JSON/Text on SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asin: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    base_price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    metrics = relationship("DailyMetric", back_populates="product", cascade="all, delete-orphan")
    signals = relationship("DetectedSignal", back_populates="product", cascade="all, delete-orphan")
    listing = relationship("ListingData", back_populates="product", uselist=False, cascade="all, delete-orphan")
    pricing = relationship("PricingData", back_populates="product", uselist=False, cascade="all, delete-orphan")
    inventory_config = relationship("InventoryConfig", back_populates="product", uselist=False, cascade="all, delete-orphan")


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inventory_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_buy_box: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ad_spend: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    ad_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ad_sales: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))

    product = relationship("Product", back_populates="metrics")

    __table_args__ = (
        Index("idx_daily_metrics_product_date", "product_id", "date"),
    )


class DetectedSignal(Base):
    __tablename__ = "detected_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    detected_at: Mapped[str] = mapped_column(String(64), nullable=False)

    product = relationship("Product", back_populates="signals")


class ListingData(Base):
    __tablename__ = "listing_data"

    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False)
    bullets: Mapped[List[str]] = mapped_column(UniversalJSON, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    backend_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    image_urls: Mapped[List[str]] = mapped_column(UniversalJSON, nullable=False)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    listing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    product = relationship("Product", back_populates="listing")


class ListingAudit(Base):
    __tablename__ = "listing_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    category_scores: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    failed_rules: Mapped[List[Any]] = mapped_column(UniversalJSON, nullable=False)
    warnings: Mapped[List[Any]] = mapped_column(UniversalJSON, nullable=False)
    passed_rules: Mapped[List[Any]] = mapped_column(UniversalJSON, nullable=False)
    analyzed_at: Mapped[str] = mapped_column(String(64), nullable=False)


class ListingRecommendation(Base):
    __tablename__ = "listing_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("listing_audits.id", ondelete="SET NULL"), nullable=True)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    current_value: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)
    changes: Mapped[List[Any]] = mapped_column(UniversalJSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class PricingData(Base):
    __tablename__ = "pricing_data"

    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    cogs: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    referral_fee_pct: Mapped[decimal.Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    fulfillment_fee: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    closing_fee: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    packaging_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    inbound_freight: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    ad_cost_per_unit: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    returns_allowance: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    other_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    target_margin_pct: Mapped[decimal.Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    min_margin_pct: Mapped[decimal.Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=decimal.Decimal("0.1000"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    product = relationship("Product", back_populates="pricing")


class PricingObservation(Base):
    __tablename__ = "pricing_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    competitor: Mapped[str] = mapped_column(String(128), nullable=False)
    competitor_asin: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    shipping_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    landed_price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=decimal.Decimal("0.0000"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    match_tier: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="TIER_1_SAME_ASIN")
    is_buy_box_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fulfillment_channel: Mapped[str] = mapped_column(String(32), nullable=False, default="FBA")
    condition_type: Mapped[str] = mapped_column(String(32), nullable=False, default="New")
    seller_rating: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(3, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observed_at: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="high")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CompetitorMatch(Base):
    __tablename__ = "competitor_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_asin: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    candidate_title: Mapped[str] = mapped_column(Text, nullable=False)
    match_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    match_confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    match_method: Mapped[str] = mapped_column(String(64), nullable=False)
    matched_fields: Mapped[List[str]] = mapped_column(UniversalJSON, nullable=False)
    mismatched_fields: Mapped[List[str]] = mapped_column(UniversalJSON, nullable=False)
    seller_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    reviewed_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PricingAnalysis(Base):
    __tablename__ = "pricing_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    current_price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    variable_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    contribution: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    margin_pct: Mapped[decimal.Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    breakeven_price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    target_margin_price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    price_state: Mapped[str] = mapped_column(String(64), nullable=False)
    recommended_low: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    recommended_high: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    analyzed_at: Mapped[str] = mapped_column(String(64), nullable=False)


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    review_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    verified_purchase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="synthetic")


class ReviewAnalysis(Base):
    __tablename__ = "review_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_rating: Mapped[decimal.Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    rating_distribution: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    negative_pct: Mapped[decimal.Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    velocity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_velocity: Mapped[int] = mapped_column(Integer, nullable=False)
    trend: Mapped[str] = mapped_column(String(32), nullable=False)
    themes: Mapped[List[Any]] = mapped_column(UniversalJSON, nullable=False)
    emerging_issues: Mapped[List[Any]] = mapped_column(UniversalJSON, nullable=False)
    analyzed_at: Mapped[str] = mapped_column(String(64), nullable=False)


class InventoryConfig(Base):
    __tablename__ = "inventory_config"

    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_days: Mapped[int] = mapped_column(Integer, nullable=False)
    moq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reorder_multiple: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_service_level: Mapped[decimal.Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=decimal.Decimal("0.9500"))

    product = relationship("Product", back_populates="inventory_config")


class IntelligenceRun(Base):
    __tablename__ = "intelligence_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    condition_json: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    action_json: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class ActionQueueItem(Base):
    __tablename__ = "action_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", index=True)
    why_panel: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(UniversalJSON, nullable=False)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProvenanceRegistryRecord(Base):
    __tablename__ = "provenance_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    marketplace_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    raw_record_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="high")
    limitations: Mapped[List[str]] = mapped_column(UniversalJSON, nullable=False)
    registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
