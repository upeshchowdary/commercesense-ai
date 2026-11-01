"""
provenance.py — Universal source provenance envelope, capability matrix, and
data source registry for CommerceSense AI v3.

Every metric, observation, and analysis carried across the system has an explicit
provenance envelope classifying its origin, authenticity, and confidence.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProvenanceEnvelope(str, Enum):
    """The 8 standardized provenance classifications defined in docs/DATA_SOURCES.md."""
    AMAZON_OFFICIAL = "AMAZON_OFFICIAL"
    PUBLIC_NEWS = "PUBLIC_NEWS"
    SELLER_INPUT = "SELLER_INPUT"
    CALCULATED = "CALCULATED"
    MODELLED = "MODELLED"
    CACHED = "CACHED"
    DEMO = "DEMO"
    MISSING = "MISSING"


def compute_record_hash(data: Any) -> str:
    """Calculates a deterministic SHA-256 hash of any python dictionary, BaseModel, or primitive."""
    if data is None:
        return hashlib.sha256(b"").hexdigest()
    if isinstance(data, BaseModel):
        serialized = data.model_dump_json()
    else:
        serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class SourceEnvelope(BaseModel):
    """Universal source provenance envelope required for all ingested and computed records."""
    source_id: str = Field(description="Unique identifier of data source")
    provider: str = Field(description="Underlying provider name (e.g., amzn-sp-api, gdelt, ollama)")
    source_type: ProvenanceEnvelope = Field(description="One of the 8 canonical provenance envelopes")
    marketplace_id: Optional[str] = Field(default=None, description="Amazon Marketplace ID (e.g. A21TJRUUN4KGV)")
    currency: Optional[str] = Field(default=None, description="ISO Currency code (e.g. INR, USD)")
    timestamps: Dict[str, str] = Field(
        default_factory=lambda: {"recorded_at": datetime.now(timezone.utc).isoformat()},
        description="ISO-8601 timestamps for retrieval, observation, and calculation",
    )
    raw_record_hash: Optional[str] = Field(default=None, description="SHA-256 hash of raw input data")
    confidence: str = Field(default="high", description="Confidence rating: high, medium, low")
    limitations: List[str] = Field(default_factory=list, description="Known caveats or limitations")

    @classmethod
    def create(
        cls,
        source_id: str,
        provider: str,
        source_type: ProvenanceEnvelope,
        raw_data: Any = None,
        marketplace_id: Optional[str] = None,
        currency: Optional[str] = None,
        confidence: str = "high",
        limitations: Optional[List[str]] = None,
        extra_timestamps: Optional[Dict[str, str]] = None,
    ) -> "SourceEnvelope":
        ts = {"recorded_at": datetime.now(timezone.utc).isoformat()}
        if extra_timestamps:
            ts.update(extra_timestamps)

        record_hash = compute_record_hash(raw_data) if raw_data is not None else None

        return cls(
            source_id=source_id,
            provider=provider,
            source_type=source_type,
            marketplace_id=marketplace_id,
            currency=currency,
            timestamps=ts,
            raw_record_hash=record_hash,
            confidence=confidence,
            limitations=limitations or [],
        )


# =====================================================================
# Capability Matrix & Data Source Registry
# =====================================================================

class SourceCapability(str, Enum):
    SALES_TRAFFIC_REPORTS = "sales_traffic_reports"
    INVENTORY_SUMMARIES = "inventory_summaries"
    COMPETITIVE_PRICING = "competitive_pricing"
    CATALOG_ITEMS = "catalog_items"
    BRAND_ANALYTICS = "brand_analytics"
    MACRO_NEWS_SENTIMENT = "macro_news_sentiment"
    RSS_FEEDS = "rss_feeds"
    GOOGLE_TRENDS_PARSER = "google_trends_parser"
    STRUCTURED_EXPLANATIONS = "structured_explanations"
    TITLE_REWRITING = "title_rewriting"
    DETERMINISTIC_PRICING = "deterministic_pricing"
    INVENTORY_DAYS_OF_COVER = "inventory_days_of_cover"
    LISTING_AUDIT = "listing_audit"
    REVIEW_THEME_EXTRACTION = "review_theme_extraction"
    OPPORTUNITY_ATTENTION_SCORE = "opportunity_attention_score"
    CSV_INGESTION = "csv_ingestion"
    SYNTHETIC_DATA_GENERATION = "synthetic_data_generation"


DATA_SOURCE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "amzn-sp-api": {
        "name": "Amazon Selling Partner API (SP-API)",
        "source_type": ProvenanceEnvelope.AMAZON_OFFICIAL,
        "is_paid": False,
        "is_allowed": True,
        "requires_credentials": True,
        "default_marketplace": "A21TJRUUN4KGV",
        "capabilities": [
            SourceCapability.SALES_TRAFFIC_REPORTS,
            SourceCapability.INVENTORY_SUMMARIES,
            SourceCapability.COMPETITIVE_PRICING,
            SourceCapability.CATALOG_ITEMS,
            SourceCapability.BRAND_ANALYTICS,
        ],
        "limitations": [
            "Requires valid Amazon SP-API developer registration and LWA credentials",
            "Reports are asynchronous and subject to Amazon generation latencies (1-15m)",
        ],
    },
    "gdelt": {
        "name": "GDELT 2.0 Doc API",
        "source_type": ProvenanceEnvelope.PUBLIC_NEWS,
        "is_paid": False,
        "is_allowed": True,
        "requires_credentials": False,
        "capabilities": [
            SourceCapability.MACRO_NEWS_SENTIMENT,
        ],
        "limitations": [
            "Free public REST API, subject to rate limits and upstream latency",
        ],
    },
    "rss_feeds": {
        "name": "Public Category & Regulatory RSS Feeds",
        "source_type": ProvenanceEnvelope.PUBLIC_NEWS,
        "is_paid": False,
        "is_allowed": True,
        "requires_credentials": False,
        "capabilities": [
            SourceCapability.RSS_FEEDS,
        ],
        "limitations": [
            "Dependent on syndication availability of target trade publications",
        ],
    },
    "ollama": {
        "name": "Local Ollama LLM Service",
        "source_type": ProvenanceEnvelope.MODELLED,
        "is_paid": False,
        "is_allowed": True,
        "requires_credentials": False,
        "capabilities": [
            SourceCapability.STRUCTURED_EXPLANATIONS,
            SourceCapability.TITLE_REWRITING,
        ],
        "limitations": [
            "Requires locally running Ollama daemon; falls back to deterministic rules when offline",
            "Inference speed depends on local hardware (GPU/CPU)",
        ],
    },
    "deterministic_engines": {
        "name": "Core Deterministic Python Rule Engines",
        "source_type": ProvenanceEnvelope.CALCULATED,
        "is_paid": False,
        "is_allowed": True,
        "requires_credentials": False,
        "capabilities": [
            SourceCapability.DETERMINISTIC_PRICING,
            SourceCapability.INVENTORY_DAYS_OF_COVER,
            SourceCapability.LISTING_AUDIT,
            SourceCapability.REVIEW_THEME_EXTRACTION,
            SourceCapability.OPPORTUNITY_ATTENTION_SCORE,
        ],
        "limitations": [
            "Zero external API dependencies; pure local mathematical calculations",
        ],
    },
    "csv_provider": {
        "name": "Seller CSV File Upload Engine",
        "source_type": ProvenanceEnvelope.SELLER_INPUT,
        "is_paid": False,
        "is_allowed": True,
        "requires_credentials": False,
        "capabilities": [
            SourceCapability.CSV_INGESTION,
            SourceCapability.GOOGLE_TRENDS_PARSER,
        ],
        "limitations": [
            "Requires manual seller upload and format adherence to predefined CSV templates",
        ],
    },
    "demo_provider": {
        "name": "Seeded Synthetic Demo Dataset",
        "source_type": ProvenanceEnvelope.DEMO,
        "is_paid": False,
        "is_allowed": True,
        "requires_credentials": False,
        "capabilities": [
            SourceCapability.SYNTHETIC_DATA_GENERATION,
        ],
        "limitations": [
            "Synthetic data generated deterministically (SEED=42) for testing and evaluation only",
        ],
    },
    # Prohibited/Blocked paid providers:
    "tavily": {
        "name": "Tavily Search API",
        "source_type": ProvenanceEnvelope.PUBLIC_NEWS,
        "is_paid": True,
        "is_allowed": False,
        "requires_credentials": True,
        "capabilities": [],
        "limitations": ["Blocked under FREE_ONLY=true hard gate policy"],
    },
    "gemini": {
        "name": "Google Gemini Hosted API",
        "source_type": ProvenanceEnvelope.MODELLED,
        "is_paid": True,
        "is_allowed": False,
        "requires_credentials": True,
        "capabilities": [],
        "limitations": ["Blocked under FREE_ONLY=true hard gate policy"],
    },
    "openai": {
        "name": "OpenAI Hosted API",
        "source_type": ProvenanceEnvelope.MODELLED,
        "is_paid": True,
        "is_allowed": False,
        "requires_credentials": True,
        "capabilities": [],
        "limitations": ["Blocked under FREE_ONLY=true hard gate policy"],
    },
    "anthropic": {
        "name": "Anthropic Claude Hosted API",
        "source_type": ProvenanceEnvelope.MODELLED,
        "is_paid": True,
        "is_allowed": False,
        "requires_credentials": True,
        "capabilities": [],
        "limitations": ["Blocked under FREE_ONLY=true hard gate policy"],
    },
    "serpapi": {
        "name": "SerpAPI Search Engine Scraper",
        "source_type": ProvenanceEnvelope.PUBLIC_NEWS,
        "is_paid": True,
        "is_allowed": False,
        "requires_credentials": True,
        "capabilities": [],
        "limitations": ["Blocked under FREE_ONLY=true hard gate policy"],
    },
    "apify": {
        "name": "Apify Web Scraping Actor Platform",
        "source_type": ProvenanceEnvelope.PUBLIC_NEWS,
        "is_paid": True,
        "is_allowed": False,
        "requires_credentials": True,
        "capabilities": [],
        "limitations": ["Blocked under FREE_ONLY=true hard gate policy"],
    },
}


def get_source_registry_entry(provider_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves source configuration and capabilities from the registry."""
    return DATA_SOURCE_REGISTRY.get(provider_id)


def is_provider_allowed(provider_id: str, free_only: bool = True) -> bool:
    """Checks whether a provider is permitted under current operational policies."""
    entry = DATA_SOURCE_REGISTRY.get(provider_id)
    if not entry:
        return False
    if free_only and entry.get("is_paid", False):
        return False
    return entry.get("is_allowed", True)


def get_providers_for_capability(capability: SourceCapability, free_only: bool = True) -> List[str]:
    """Finds all providers registered with a specific capability."""
    allowed = []
    for pid, meta in DATA_SOURCE_REGISTRY.items():
        if free_only and meta.get("is_paid", False):
            continue
        if capability in meta.get("capabilities", []):
            allowed.append(pid)
    return allowed


def register_source_envelope_in_db(envelope: SourceEnvelope, session: Optional[Any] = None) -> Any:
    """Persists a SourceEnvelope into the PostgreSQL / SQLite provenance_registry table."""
    if session is None:
        try:
            from db.session import get_session
            with get_session() as s:
                result = register_source_envelope_in_db(envelope, s)
                s.commit()
                return result
        except Exception:
            return None

    from db.models import ProvenanceRegistryRecord

    rec = session.query(ProvenanceRegistryRecord).filter_by(source_id=envelope.source_id).first()
    if not rec:
        rec = ProvenanceRegistryRecord(
            source_id=envelope.source_id,
            provider=envelope.provider,
            source_type=envelope.source_type.value if hasattr(envelope.source_type, "value") else str(envelope.source_type),
            marketplace_id=envelope.marketplace_id,
            currency=envelope.currency,
            raw_record_hash=envelope.raw_record_hash,
            confidence=envelope.confidence,
            limitations=envelope.limitations,
        )
        session.add(rec)
    else:
        rec.provider = envelope.provider
        rec.source_type = envelope.source_type.value if hasattr(envelope.source_type, "value") else str(envelope.source_type)
        rec.marketplace_id = envelope.marketplace_id
        rec.currency = envelope.currency
        rec.raw_record_hash = envelope.raw_record_hash
        rec.confidence = envelope.confidence
        rec.limitations = envelope.limitations
    return rec
