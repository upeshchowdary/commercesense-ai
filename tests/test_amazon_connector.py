"""
test_amazon_connector.py — Test suite for Phase 2: Official Amazon SP-API SDK
Integration, Rate Limiting, LWA Token Management, Report Ingestion, Capability Matrix,
and CSV/Demo Mode Fallback Isolation.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api.main import app
from db.models import Base, DailyMetric, ListingData, Product, ProvenanceRegistryRecord
from providers.amazon_data import (
    CSVDataProvider,
    DemoDataProvider,
    SPAPIProvider,
    get_amazon_data_provider,
)
from providers.amazon_sp_api import (
    DEFAULT_MARKETPLACE_ID,
    MARKETPLACES,
    AmazonAuthenticationError,
    AmazonMarketplace,
    AmazonSPAPIAdapter,
    CapabilityStatus,
    LWATokenManager,
    TokenBucketRateLimiter,
    get_amazon_sp_api_adapter,
    get_marketplace,
    ingest_fba_inventory_report,
    ingest_listings_item,
    ingest_sales_and_traffic_report,
    parse_fba_inventory_report,
    parse_listings_item,
    parse_sales_and_traffic_report,
)
from providers.provenance import ProvenanceEnvelope


@pytest.fixture
def in_memory_db():
    """Isolated in-memory SQLite database for testing ingestion and persistence."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_lwa_transport():
    """Mock LWA token exchange transport returning valid token responses."""
    def transport(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload.get("refresh_token") == "invalid_refresh_token":
            raise requests_error_helper(400, "invalid_grant: The provided authorization grant is invalid")
        return {
            "access_token": "Atza|mock_access_token_12345",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": payload.get("refresh_token"),
        }
    return transport


def requests_error_helper(status_code: int, detail: str):
    import requests
    response = requests.Response()
    response.status_code = status_code
    response._content = detail.encode("utf-8")
    return requests.HTTPError(response=response)


# =====================================================================
# 1. Marketplaces & Endpoint Routing Tests
# =====================================================================

def test_default_marketplace_configuration():
    """Verifies default marketplace is Amazon India (A21TJRUUN4KGV) using European regional endpoint."""
    mp = get_marketplace(DEFAULT_MARKETPLACE_ID)
    assert mp is not None
    assert mp.marketplace_id == "A21TJRUUN4KGV"
    assert mp.country_code == "IN"
    assert mp.region == "EU"
    assert mp.endpoint == "https://sellingpartnerapi-eu.amazon.com"
    assert mp.currency == "INR"
    assert mp.supports_brand_analytics is True


def test_global_marketplaces_configuration():
    """Verifies US, CA, UK, DE, and JP marketplaces are properly mapped with correct endpoints."""
    # US
    us = get_marketplace("ATVPDKIKX0DER")
    assert us is not None
    assert us.region == "NA"
    assert us.endpoint == "https://sellingpartnerapi-na.amazon.com"
    assert us.currency == "USD"

    # UK
    uk = get_marketplace("A1F83G8C2ARO7P")
    assert uk is not None
    assert uk.region == "EU"
    assert uk.endpoint == "https://sellingpartnerapi-eu.amazon.com"
    assert uk.currency == "GBP"

    # Japan
    jp = get_marketplace("A1VC38T7YXB528")
    assert jp is not None
    assert jp.region == "FE"
    assert jp.endpoint == "https://sellingpartnerapi-fe.amazon.com"
    assert jp.currency == "JPY"

    # Unsupported marketplace ID
    assert get_marketplace("NON_EXISTENT_ID") is None


# =====================================================================
# 2. Token Bucket Rate Limiter Tests
# =====================================================================

def test_rate_limiter_token_acquisition_and_burst():
    """Tests token bucket acquisition, burst capacity limits, and deduction."""
    limiter = TokenBucketRateLimiter(plans={"test_op": (10.0, 5.0)})

    # Fresh bucket has burst capacity (5.0 tokens)
    status = limiter.get_status("test_op")
    assert status["burst_capacity"] == 5.0
    assert status["available_tokens"] == 5.0
    assert status["is_throttled"] is False

    # Acquire 3 tokens
    assert limiter.acquire("test_op", tokens=3.0, block=False) is True
    status = limiter.get_status("test_op")
    assert status["available_tokens"] <= 2.1

    # Acquire remaining 2 tokens
    assert limiter.acquire("test_op", tokens=2.0, block=False) is True

    # Immediate next acquire should fail without blocking
    assert limiter.acquire("test_op", tokens=1.0, block=False) is False
    assert limiter.is_rate_limited("test_op") is True


def test_rate_limiter_replenishment():
    """Tests that tokens replenish over elapsed time according to defined rate."""
    limiter = TokenBucketRateLimiter(plans={"fast_op": (50.0, 10.0)})
    # Drain bucket
    assert limiter.acquire("fast_op", tokens=10.0, block=False) is True

    # Sleep 0.1s => replenishes approx 5 tokens
    time.sleep(0.1)
    status = limiter.get_status("fast_op")
    assert status["available_tokens"] >= 4.0

    # Can acquire again
    assert limiter.acquire("fast_op", tokens=3.0, block=False) is True


def test_rate_limiter_429_backoff_handling():
    """Tests HTTP 429 Retry-After header and exponential backoff cooldown."""
    limiter = TokenBucketRateLimiter(plans={"report_op": (0.0167, 15.0)})

    # Explicit Retry-After header value (e.g. 2.0 seconds)
    duration = limiter.record_throttle("report_op", retry_after=2.0)
    assert duration == 2.0
    assert limiter.is_rate_limited("report_op") is True

    status = limiter.get_status("report_op")
    assert status["is_throttled"] is True
    assert status["throttled_remaining_sec"] > 0.0

    # Acquire must fail non-blocking while throttled
    assert limiter.acquire("report_op", tokens=1.0, block=False) is False

    # Exponential backoff when retry_after is None
    limiter.reset("report_op")
    dur1 = limiter.record_throttle("report_op", retry_after=None, backoff_base=2.0)
    assert dur1 >= 2.0  # base^1 + jitter

    dur2 = limiter.record_throttle("report_op", retry_after=None, backoff_base=2.0)
    assert dur2 >= 4.0  # base^2 + jitter

    # On success, consecutive throttle counter resets
    limiter.on_success("report_op")
    assert limiter.get_status("report_op")["consecutive_throttles"] == 0


# =====================================================================
# 3. LWA Token Manager & Proactive Refresh Tests
# =====================================================================

def test_lwa_token_manager_caching_and_proactive_refresh(mock_lwa_transport):
    """Tests thread-safe in-memory caching and proactive expiry refresh."""
    call_count = 0

    def counting_transport(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal call_count
        call_count += 1
        return {
            "access_token": f"Atza|token_call_{call_count}",
            "expires_in": 3600,
            "token_type": "bearer",
        }

    manager = LWATokenManager(
        client_id="amzn1.application-oa2-client.test1234",
        client_secret="test_secret_abc123",
        refresh_token="Atzr|test_refresh_token_xyz",
        proactive_refresh_seconds=300.0,
        transport_fn=counting_transport,
    )

    assert manager.is_configured() is True
    assert manager.masked_client_id == "amzn...1234"

    # First call triggers exchange
    token1 = manager.get_access_token()
    assert token1 == "Atza|token_call_1"
    assert call_count == 1
    assert manager.is_token_valid() is True

    # Immediate second call returns cached token without calling transport
    token2 = manager.get_access_token()
    assert token2 == "Atza|token_call_1"
    assert call_count == 1

    # Proactive refresh: Simulate token expiration nearing window (only 200s left < 300s threshold)
    manager.set_cached_token("Atza|token_call_1", expires_in=200.0)
    assert manager.is_token_valid() is False  # In proactive refresh window

    # get_access_token proactively triggers new token exchange
    token3 = manager.get_access_token()
    assert token3 == "Atza|token_call_2"
    assert call_count == 2
    assert manager.is_token_valid() is True

    # Force refresh forces new exchange
    token4 = manager.get_access_token(force_refresh=True)
    assert token4 == "Atza|token_call_3"
    assert call_count == 3


def test_lwa_token_manager_unconfigured_error():
    """Unconfigured token manager raises descriptive error without leaking secrets."""
    manager = LWATokenManager(client_id=None, client_secret=None, refresh_token=None)
    assert manager.is_configured() is False
    assert manager.masked_client_id is None

    with pytest.raises(AmazonAuthenticationError) as exc_info:
        manager.get_access_token()
    assert "SP-API LWA credentials not configured" in str(exc_info.value)


# =====================================================================
# 4. Report Parsing & Data Ingestion Tests
# =====================================================================

def test_parse_sales_and_traffic_report():
    """Tests parsing of GET_SALES_AND_TRAFFIC_REPORT JSON documents."""
    sample_report = {
        "reportSpecification": {
            "reportType": "GET_SALES_AND_TRAFFIC_REPORT",
            "dataStartTime": "2026-09-20",
            "dataEndTime": "2026-09-22",
            "marketplaceIds": ["A21TJRUUN4KGV"],
        },
        "salesAndTrafficByDate": [
            {
                "date": "2026-09-20",
                "salesByDate": {
                    "orderedProductSales": {"amount": 3499.50, "currencyCode": "INR"},
                    "unitsOrdered": 7,
                    "totalOrderItems": 5,
                },
                "trafficByDate": {
                    "sessions": 142,
                    "pageViews": 210,
                    "buyBoxPercentage": 85.5,
                },
            },
            {
                "date": "2026-09-21",
                "salesByDate": {
                    "orderedProductSales": {"amount": 5999.00, "currencyCode": "INR"},
                    "unitsOrdered": 12,
                    "totalOrderItems": 10,
                },
                "trafficByDate": {
                    "sessions": 260,
                    "pageViews": 380,
                    "buyBoxPercentage": 92.0,
                },
            },
        ],
    }

    records = parse_sales_and_traffic_report(sample_report)
    assert len(records) == 2

    r1 = records[0]
    assert r1["date"] == "2026-09-20"
    assert r1["units_sold"] == 7
    assert r1["total_orders"] == 5
    assert r1["ordered_sales"] == Decimal("3499.50")
    assert r1["currency"] == "INR"
    assert r1["sessions"] == 142
    assert r1["page_views"] == 210
    assert r1["buy_box_percentage"] == 85.5

    # Also test per-ASIN breakdown
    sample_asin_report = {
        "reportSpecification": {"dataEndTime": "2026-09-22"},
        "salesAndTrafficByAsin": [
            {
                "parentAsin": "B00PARENT1",
                "childAsin": "B00CHILD01",
                "sku": "P001",
                "salesByAsin": {
                    "orderedProductSales": {"amount": 1200.00, "currencyCode": "INR"},
                    "unitsOrdered": 4,
                    "totalOrderItems": 3,
                },
                "trafficByAsin": {
                    "sessions": 80,
                    "pageViews": 120,
                    "buyBoxPercentage": 95.0,
                },
            }
        ],
    }
    asin_records = parse_sales_and_traffic_report(sample_asin_report)
    assert len(asin_records) == 1
    assert asin_records[0]["sku"] == "P001"
    assert asin_records[0]["asin"] == "B00CHILD01"
    assert asin_records[0]["units_sold"] == 4


def test_ingest_sales_and_traffic_report_into_db(in_memory_db):
    """Verifies that sales & traffic reports persist into DailyMetric and register AMAZON_OFFICIAL provenance."""
    sample_report = {
        "reportSpecification": {"marketplaceIds": ["A21TJRUUN4KGV"]},
        "salesAndTrafficByDate": [
            {
                "date": "2026-09-24",
                "salesByDate": {
                    "orderedProductSales": {"amount": 2500.00, "currencyCode": "INR"},
                    "unitsOrdered": 5,
                    "totalOrderItems": 4,
                },
                "trafficByDate": {
                    "sessions": 100,
                    "pageViews": 150,
                    "buyBoxPercentage": 90.0,
                },
            }
        ],
    }

    metrics = ingest_sales_and_traffic_report(
        report_data=sample_report,
        session=in_memory_db,
        marketplace_id="A21TJRUUN4KGV",
        default_product_id="P001",
    )
    in_memory_db.commit()

    assert len(metrics) == 1
    metric = in_memory_db.query(DailyMetric).filter_by(product_id="P001", date="2026-09-24").first()
    assert metric is not None
    assert metric.units_sold == 5
    assert metric.has_buy_box is True
    assert metric.ad_sales == Decimal("2500.00")

    # Verify SourceEnvelope provenance registration
    provenance_rec = in_memory_db.query(ProvenanceRegistryRecord).filter_by(
        source_id="amzn-sp-api:sales_traffic:P001:2026-09-24"
    ).first()
    assert provenance_rec is not None
    assert provenance_rec.provider == "amzn-sp-api"
    assert provenance_rec.source_type == ProvenanceEnvelope.AMAZON_OFFICIAL.value
    assert provenance_rec.marketplace_id == "A21TJRUUN4KGV"


def test_parse_and_ingest_fba_inventory_report(in_memory_db):
    """Tests parsing TSV inventory report and persisting fulfillable inventory into DailyMetric."""
    tsv_content = (
        "sku\tasin\tproduct-name\tafn-fulfillable-quantity\tafn-reserved-quantity\tafn-unsellable-quantity\n"
        "P001\tB00ABC123\tErgonomic Pillow\t142\t8\t2\n"
        "P002\tB00XYZ456\tWeighted Blanket\t55\t3\t0\n"
    )

    # 1. Parse
    items = parse_fba_inventory_report(tsv_content)
    assert len(items) == 2
    assert items[0]["sku"] == "P001"
    assert items[0]["fulfillable_quantity"] == 142
    assert items[0]["reserved_quantity"] == 8
    assert items[1]["sku"] == "P002"
    assert items[1]["fulfillable_quantity"] == 55

    # 2. Ingest
    results = ingest_fba_inventory_report(
        report_data=tsv_content,
        session=in_memory_db,
        report_date="2026-09-24",
        marketplace_id="A21TJRUUN4KGV",
    )
    in_memory_db.commit()

    assert len(results) == 2
    m1 = in_memory_db.query(DailyMetric).filter_by(product_id="P001", date="2026-09-24").first()
    assert m1 is not None
    assert m1.inventory_level == 142

    m2 = in_memory_db.query(DailyMetric).filter_by(product_id="P002", date="2026-09-24").first()
    assert m2 is not None
    assert m2.inventory_level == 55

    # Check provenance
    prov = in_memory_db.query(ProvenanceRegistryRecord).filter_by(
        source_id="amzn-sp-api:inventory:P001:2026-09-24"
    ).first()
    assert prov is not None
    assert prov.source_type == ProvenanceEnvelope.AMAZON_OFFICIAL.value


def test_parse_and_ingest_listings_item(in_memory_db):
    """Tests parsing getListingsItem payload and persisting ListingData with AMAZON_OFFICIAL provenance."""
    sample_item = {
        "sku": "P001",
        "summaries": [
            {
                "asin": "B00TESTASIN1",
                "itemName": "Ergonomic Memory Foam Pillow with Cooling Gel",
                "productType": "HOME_BED_AND_BATH",
                "status": ["BUYABLE", "DISCOVERABLE"],
                "mainImage": {"link": "https://m.media-amazon.com/images/I/71test.jpg"},
            }
        ],
        "attributes": {
            "brand": [{"value": "RestEasy"}],
            "bullet_point": [
                {"value": "Ergonomic cervical contour design"},
                {"value": "High density memory foam with cooling gel"},
            ],
            "product_description": [
                {"value": "Premium orthopedic memory foam pillow for neck pain relief."}
            ],
        },
    }

    # 1. Parse
    parsed = parse_listings_item(sample_item)
    assert parsed["sku"] == "P001"
    assert parsed["asin"] == "B00TESTASIN1"
    assert parsed["title"] == "Ergonomic Memory Foam Pillow with Cooling Gel"
    assert parsed["brand"] == "RestEasy"
    assert len(parsed["bullets"]) == 2
    assert parsed["status"] == "ACTIVE"

    # 2. Ingest
    listing = ingest_listings_item(
        item_data=sample_item,
        session=in_memory_db,
        marketplace_id="A21TJRUUN4KGV",
    )
    in_memory_db.commit()

    assert listing.product_id == "P001"
    assert listing.brand == "RestEasy"
    assert len(listing.bullets) == 2
    assert listing.listing_status == "ACTIVE"

    # Check Product was updated
    prod = in_memory_db.query(Product).filter_by(product_id="P001").first()
    assert prod is not None
    assert prod.asin == "B00TESTASIN1"

    # Check Provenance
    prov = in_memory_db.query(ProvenanceRegistryRecord).filter_by(
        source_id="amzn-sp-api:listing:P001"
    ).first()
    assert prov is not None
    assert prov.source_type == ProvenanceEnvelope.AMAZON_OFFICIAL.value


# =====================================================================
# 5. Capability Matrix & Granular Status Tests
# =====================================================================

def test_capability_matrix_states():
    """
    Tests granular capability statuses:
    AVAILABLE, NEEDS_ROLE, NEEDS_BRAND_REGISTRY, MARKETPLACE_UNSUPPORTED, NOT_AUTHORISED, RATE_LIMITED.
    """
    # 1. NOT_AUTHORISED (unconfigured credentials)
    unauth_adapter = AmazonSPAPIAdapter(
        token_manager=LWATokenManager(client_id=None, client_secret=None, refresh_token=None)
    )
    assert unauth_adapter.get_capability_status("sales_traffic_reports") == CapabilityStatus.NOT_AUTHORISED

    # 2. Fully authorized adapter with all permissions
    auth_manager = LWATokenManager(
        client_id="amzn1.test", client_secret="secret", refresh_token="refresh"
    )
    auth_adapter = AmazonSPAPIAdapter(
        token_manager=auth_manager,
        has_brand_registry=True,
        granted_roles=["reports", "inventory", "listings", "pricing", "brand_analytics"],
    )
    assert auth_adapter.get_capability_status("sales_traffic_reports") == CapabilityStatus.AVAILABLE
    assert auth_adapter.get_capability_status("inventory_summaries") == CapabilityStatus.AVAILABLE
    assert auth_adapter.get_capability_status("brand_analytics") == CapabilityStatus.AVAILABLE

    # 3. NEEDS_ROLE: missing pricing role
    no_pricing_adapter = AmazonSPAPIAdapter(
        token_manager=auth_manager,
        has_brand_registry=True,
        granted_roles=["reports", "inventory", "listings"],  # missing pricing
    )
    assert no_pricing_adapter.get_capability_status("competitive_pricing") == CapabilityStatus.NEEDS_ROLE
    assert no_pricing_adapter.get_capability_status("sales_traffic_reports") == CapabilityStatus.AVAILABLE

    # 4. NEEDS_BRAND_REGISTRY: missing Brand Registry enrollment
    no_br_adapter = AmazonSPAPIAdapter(
        token_manager=auth_manager,
        has_brand_registry=False,
        granted_roles=["reports", "inventory", "listings", "pricing", "brand_analytics"],
    )
    assert no_br_adapter.get_capability_status("brand_analytics") == CapabilityStatus.NEEDS_BRAND_REGISTRY

    # 5. MARKETPLACE_UNSUPPORTED: Singapore doesn't support brand analytics
    sg_adapter = AmazonSPAPIAdapter(
        marketplace_id="A19VAU5U5O7RUS",  # Singapore
        token_manager=auth_manager,
        has_brand_registry=True,
        granted_roles=["brand_analytics"],
    )
    assert sg_adapter.get_capability_status("brand_analytics") == CapabilityStatus.MARKETPLACE_UNSUPPORTED

    # 6. RATE_LIMITED: throttled operation bucket
    limiter = TokenBucketRateLimiter()
    limiter.record_throttle("get_report", retry_after=10.0)
    throttled_adapter = AmazonSPAPIAdapter(
        token_manager=auth_manager,
        rate_limiter=limiter,
        granted_roles=["reports"],
    )
    assert throttled_adapter.get_capability_status("sales_traffic_reports") == CapabilityStatus.RATE_LIMITED


# =====================================================================
# 6. REST API Endpoints Tests (/connections/amazon & /connections/capabilities)
# =====================================================================

def test_api_connections_amazon():
    """Tests GET /api/v1/connections/amazon diagnostics endpoint."""
    client = TestClient(app)

    # Call endpoint
    resp = client.get("/api/v1/connections/amazon")
    assert resp.status_code == 200
    data = resp.json()

    assert "connected" in data
    assert "status" in data
    assert "marketplace" in data
    assert data["marketplace"]["marketplace_id"] == "A21TJRUUN4KGV"
    assert data["marketplace"]["endpoint"] == "https://sellingpartnerapi-eu.amazon.com"
    assert "token" in data
    assert "capabilities" in data
    assert "rate_limits" in data
    assert data["provenance"]["provider"] == "amzn-sp-api"

    # Also test /api/connections/amazon prefix equivalence
    resp2 = client.get("/api/connections/amazon")
    assert resp2.status_code == 200
    assert resp2.json()["marketplace"]["marketplace_id"] == "A21TJRUUN4KGV"


def test_api_connections_capabilities():
    """Tests GET /api/v1/connections/capabilities capability matrix endpoint."""
    client = TestClient(app)

    resp = client.get("/api/v1/connections/capabilities")
    assert resp.status_code == 200
    data = resp.json()

    assert "capabilities" in data
    caps = {c["id"]: c for c in data["capabilities"]}

    # Amazon capabilities
    assert "sales_traffic_reports" in caps
    assert "inventory_summaries" in caps
    assert "listings_items" in caps
    assert "competitive_pricing" in caps
    assert "brand_analytics" in caps

    # Free-First / Public capabilities
    assert "macro_news_sentiment" in caps
    assert caps["macro_news_sentiment"]["status"] == "AVAILABLE"
    assert "rss_feeds" in caps
    assert "structured_explanations" in caps
    assert "csv_ingestion" in caps
    assert "synthetic_demo_data" in caps


def test_api_connections_ingest_report(in_memory_db):
    """Tests POST /api/v1/connections/amazon/ingest report ingestion endpoint."""
    from db.session import get_db

    client = TestClient(app)

    def override_get_db():
        yield in_memory_db

    app.dependency_overrides[get_db] = override_get_db

    sample_report = {
        "reportSpecification": {"marketplaceIds": ["A21TJRUUN4KGV"]},
        "salesAndTrafficByDate": [
            {
                "date": "2026-09-24",
                "salesByDate": {
                    "orderedProductSales": {"amount": 1850.00, "currencyCode": "INR"},
                    "unitsOrdered": 3,
                    "totalOrderItems": 3,
                },
                "trafficByDate": {
                    "sessions": 50,
                    "pageViews": 80,
                    "buyBoxPercentage": 95.0,
                },
            }
        ],
    }

    try:
        resp = client.post(
            "/api/v1/connections/amazon/ingest",
            json={
                "report_type": "GET_SALES_AND_TRAFFIC_REPORT",
                "report_payload": sample_report,
                "product_id": "P001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["records_ingested"] == 1
        assert data["provenance"] == ProvenanceEnvelope.AMAZON_OFFICIAL.value
    finally:
        app.dependency_overrides.pop(get_db, None)


# =====================================================================
# 7. CSV Fallback & Demo Mode Isolation Tests
# =====================================================================

def test_csv_fallback_and_demo_provider_isolation():
    """
    Verifies that when SP-API is unconfigured or ENABLE_SP_API is false,
    the application falls back seamlessly to DemoDataProvider or CSVDataProvider
    with zero cross-contamination.
    """
    # 1. Default fallback is DemoDataProvider
    provider = get_amazon_data_provider()
    assert isinstance(provider, DemoDataProvider)
    assert provider.name == "demo"
    assert provider.is_configured() is True

    # 2. When SP-API is not configured, SPAPIProvider reports unconfigured
    sp = SPAPIProvider()
    # In test environment without SP-API credentials, is_configured() is False
    if not sp.is_configured():
        with pytest.raises(NotImplementedError):
            sp.get_listing("B00EXAMPLE")

    # 3. CSVDataProvider is always ready
    csv_prov = CSVDataProvider()
    assert csv_prov.name == "csv"
    assert csv_prov.is_configured() is True
