"""
test_provenance.py — Tests for universal source provenance envelope and capability matrix.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from providers.provenance import (
    DATA_SOURCE_REGISTRY,
    ProvenanceEnvelope,
    SourceCapability,
    SourceEnvelope,
    compute_record_hash,
    get_providers_for_capability,
    get_source_registry_entry,
    is_provider_allowed,
)


def test_provenance_envelope_canonical_values():
    """Confirms all 8 canonical provenance envelopes are defined per docs/DATA_SOURCES.md."""
    expected = {
        "AMAZON_OFFICIAL",
        "PUBLIC_NEWS",
        "SELLER_INPUT",
        "CALCULATED",
        "MODELLED",
        "CACHED",
        "DEMO",
        "MISSING",
    }
    actual = {e.value for e in ProvenanceEnvelope}
    assert actual == expected


def test_source_envelope_creation_and_hash():
    """Verifies creation of SourceEnvelope with automatic hash computation."""
    raw_payload = {"asin": "B01N5IB20Q", "price": 49.99, "currency": "USD"}
    hash1 = compute_record_hash(raw_payload)

    # Hash must be deterministic regardless of key order
    reordered_payload = {"currency": "USD", "price": 49.99, "asin": "B01N5IB20Q"}
    hash2 = compute_record_hash(reordered_payload)
    assert hash1 == hash2

    envelope = SourceEnvelope.create(
        source_id="sp_api_pricing",
        provider="amzn-sp-api",
        source_type=ProvenanceEnvelope.AMAZON_OFFICIAL,
        raw_data=raw_payload,
        marketplace_id="A21TJRUUN4KGV",
        currency="INR",
        confidence="high",
        limitations=["Delayed up to 15 minutes"],
    )

    assert envelope.source_id == "sp_api_pricing"
    assert envelope.provider == "amzn-sp-api"
    assert envelope.source_type == ProvenanceEnvelope.AMAZON_OFFICIAL
    assert envelope.marketplace_id == "A21TJRUUN4KGV"
    assert envelope.currency == "INR"
    assert envelope.raw_record_hash == hash1
    assert envelope.confidence == "high"
    assert "recorded_at" in envelope.timestamps
    assert envelope.limitations == ["Delayed up to 15 minutes"]


def test_source_envelope_validation():
    """Ensures invalid source types or missing required fields raise validation error."""
    with pytest.raises(ValidationError):
        SourceEnvelope(source_id="test", provider="test", source_type="UNKNOWN_ENVELOPE")  # type: ignore


def test_capability_matrix_registry():
    """Checks that data source registry correctly maps capabilities and Free-First policy."""
    sp_api = get_source_registry_entry("amzn-sp-api")
    assert sp_api is not None
    assert sp_api["is_paid"] is False
    assert SourceCapability.SALES_TRAFFIC_REPORTS in sp_api["capabilities"]

    gdelt = get_source_registry_entry("gdelt")
    assert gdelt is not None
    assert gdelt["is_paid"] is False
    assert SourceCapability.MACRO_NEWS_SENTIMENT in gdelt["capabilities"]

    tavily = get_source_registry_entry("tavily")
    assert tavily is not None
    assert tavily["is_paid"] is True
    assert tavily["is_allowed"] is False

    # Check permission check
    assert is_provider_allowed("amzn-sp-api", free_only=True) is True
    assert is_provider_allowed("gdelt", free_only=True) is True
    assert is_provider_allowed("ollama", free_only=True) is True
    assert is_provider_allowed("tavily", free_only=True) is False
    assert is_provider_allowed("gemini", free_only=True) is False


def test_get_providers_for_capability():
    """Verifies capability lookup filters out paid providers in free-only mode."""
    calc_providers = get_providers_for_capability(SourceCapability.DETERMINISTIC_PRICING, free_only=True)
    assert "deterministic_engines" in calc_providers

    llm_providers = get_providers_for_capability(SourceCapability.STRUCTURED_EXPLANATIONS, free_only=True)
    assert "ollama" in llm_providers
    assert "gemini" not in llm_providers
    assert "openai" not in llm_providers


def test_compute_record_hash_with_basemodel():
    """Verifies that compute_record_hash serializes Pydantic models deterministically."""
    from pydantic import BaseModel

    class DummyModel(BaseModel):
        sku: str
        price: float

    m1 = DummyModel(sku="P001", price=12.5)
    m2 = DummyModel(sku="P001", price=12.5)
    assert compute_record_hash(m1) == compute_record_hash(m2)


def test_register_source_envelope_in_db():
    """Verifies persistence of SourceEnvelope into relational database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from db.models import Base
    from providers.provenance import register_source_envelope_in_db

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)

    envelope = SourceEnvelope.create(
        source_id="test_env_1",
        provider="gdelt",
        source_type=ProvenanceEnvelope.PUBLIC_NEWS,
        raw_data={"article": "test"},
        confidence="high",
        limitations=["public test"],
    )

    with Session(engine) as session:
        rec = register_source_envelope_in_db(envelope, session)
        session.commit()
        assert rec.id is not None
        assert rec.source_id == "test_env_1"
        assert rec.provider == "gdelt"
