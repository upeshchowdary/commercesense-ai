"""
connections.py — Amazon Connection & Capability Matrix Router for CommerceSense AI v3.

Exposes:
  - GET /connections/amazon: Connection diagnostics, marketplace metadata,
    masked client ID, token cache status, and usage plan rate limiter state.
  - GET /connections/capabilities: Granular matrix exposing capability status
    (AVAILABLE, NEEDS_ROLE, NEEDS_BRAND_REGISTRY, MARKETPLACE_UNSUPPORTED,
    NOT_AUTHORISED, RATE_LIMITED) across all platform providers.
  - POST /connections/amazon/ingest: Authorized seller performance data ingestion
    endpoint for Sales & Traffic reports, FBA Inventory, and Listings items.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api import deps
from db.session import get_db
from providers.amazon_sp_api import (
    DEFAULT_MARKETPLACE_ID,
    AmazonSPAPIAdapter,
    CapabilityStatus,
    get_amazon_sp_api_adapter,
    get_marketplace,
)
from providers.provenance import (
    DATA_SOURCE_REGISTRY,
    ProvenanceEnvelope,
    SourceCapability,
    get_source_registry_entry,
)

router = APIRouter(tags=["connections"])


class MarketplaceInfo(BaseModel):
    marketplace_id: str
    country_code: str
    name: str
    region: str
    endpoint: str
    currency: str


class TokenStatusInfo(BaseModel):
    cached: bool
    is_valid: bool
    expires_in_seconds: Optional[float] = None
    proactive_refresh_threshold_seconds: float = 300.0


class AmazonConnectionResponse(BaseModel):
    connected: bool
    status: str
    marketplace: MarketplaceInfo
    credentials_configured: bool
    client_id_masked: Optional[str] = None
    token: TokenStatusInfo
    capabilities: Dict[str, str]
    rate_limits: Dict[str, Any]
    has_brand_registry: bool
    granted_roles: List[str]
    provenance: Dict[str, str]


class CapabilityEntry(BaseModel):
    id: str
    name: str
    provider: str
    status: str
    source_type: str
    required_role: Optional[str] = None
    marketplace_supported: bool = True
    limitations: List[str] = Field(default_factory=list)


class CapabilitiesResponse(BaseModel):
    capabilities: List[CapabilityEntry]


class IngestReportRequest(BaseModel):
    report_type: str = Field(
        ...,
        description="One of 'GET_SALES_AND_TRAFFIC_REPORT', 'GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA', 'getListingsItem'",
    )
    report_payload: Any = Field(..., description="Report JSON object or raw string")
    marketplace_id: Optional[str] = Field(default=DEFAULT_MARKETPLACE_ID)
    report_date: Optional[str] = Field(default=None, description="ISO Date (YYYY-MM-DD)")
    product_id: Optional[str] = Field(default=None, description="Target product SKU/ID override")


@router.get(
    "/connections/amazon",
    response_model=AmazonConnectionResponse,
    summary="Get Amazon SP-API connection status, diagnostics, and rate limits",
)
def get_amazon_connection(
    marketplace_id: str = Query(default=DEFAULT_MARKETPLACE_ID, description="Target Amazon Marketplace ID"),
) -> AmazonConnectionResponse:
    """
    Returns live connection status for the official Amazon SP-API SDK.
    Never exposes secret keys or credentials (masks client ID).
    """
    adapter = get_amazon_sp_api_adapter(marketplace_id=marketplace_id)
    diag = adapter.get_connection_diagnostics()

    mp = diag["marketplace"]
    marketplace_model = MarketplaceInfo(
        marketplace_id=mp["marketplace_id"],
        country_code=mp["country_code"],
        name=mp["name"],
        region=mp["region"],
        endpoint=mp["endpoint"],
        currency=mp["currency"],
    )

    token_dict = diag["token"]
    token_model = TokenStatusInfo(
        cached=token_dict["cached"],
        is_valid=token_dict["is_valid"],
        expires_in_seconds=token_dict["expires_in_seconds"],
        proactive_refresh_threshold_seconds=token_dict["proactive_refresh_threshold_seconds"],
    )

    return AmazonConnectionResponse(
        connected=diag["connected"],
        status=diag["status"],
        marketplace=marketplace_model,
        credentials_configured=diag["credentials_configured"],
        client_id_masked=diag["client_id_masked"],
        token=token_model,
        capabilities=diag["capabilities"],
        rate_limits=diag["rate_limits"],
        has_brand_registry=diag["has_brand_registry"],
        granted_roles=diag["granted_roles"],
        provenance=diag["provenance"],
    )


@router.get(
    "/connections/capabilities",
    response_model=CapabilitiesResponse,
    summary="Granular capability matrix across all data sources and SP-API roles",
)
def get_capabilities(
    marketplace_id: str = Query(default=DEFAULT_MARKETPLACE_ID),
) -> CapabilitiesResponse:
    """
    Exposes the granular capability matrix across all reports and platform providers.
    States: AVAILABLE, NEEDS_ROLE, NEEDS_BRAND_REGISTRY, MARKETPLACE_UNSUPPORTED, NOT_AUTHORISED, RATE_LIMITED.
    """
    adapter = get_amazon_sp_api_adapter(marketplace_id=marketplace_id)
    mp = get_marketplace(marketplace_id)
    is_mp_supported = mp is not None

    sp_caps = [
        CapabilityEntry(
            id="sales_traffic_reports",
            name="Sales & Traffic Reports (GET_SALES_AND_TRAFFIC_REPORT)",
            provider="amzn-sp-api",
            status=adapter.get_capability_status("sales_traffic_reports").value,
            source_type=ProvenanceEnvelope.AMAZON_OFFICIAL.value,
            required_role="reports",
            marketplace_supported=is_mp_supported,
            limitations=["Daily aggregated and per-ASIN performance data"],
        ),
        CapabilityEntry(
            id="inventory_summaries",
            name="FBA Inventory Summaries (GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA)",
            provider="amzn-sp-api",
            status=adapter.get_capability_status("inventory_summaries").value,
            source_type=ProvenanceEnvelope.AMAZON_OFFICIAL.value,
            required_role="inventory",
            marketplace_supported=is_mp_supported,
            limitations=["FBA fulfillable, reserved, and unfulfillable warehouse stock"],
        ),
        CapabilityEntry(
            id="listings_items",
            name="Catalog & Listings Items API (getListingsItem)",
            provider="amzn-sp-api",
            status=adapter.get_capability_status("listings_items").value,
            source_type=ProvenanceEnvelope.AMAZON_OFFICIAL.value,
            required_role="listings",
            marketplace_supported=is_mp_supported,
            limitations=["Official listing attributes, bullets, and image locators"],
        ),
        CapabilityEntry(
            id="competitive_pricing",
            name="Competitive Pricing API (getCompetitiveSummary)",
            provider="amzn-sp-api",
            status=adapter.get_capability_status("competitive_pricing").value,
            source_type=ProvenanceEnvelope.AMAZON_OFFICIAL.value,
            required_role="pricing",
            marketplace_supported=is_mp_supported,
            limitations=["Buy Box and competitor price observations"],
        ),
        CapabilityEntry(
            id="brand_analytics",
            name="Brand Analytics Search Terms Report",
            provider="amzn-sp-api",
            status=adapter.get_capability_status("brand_analytics").value,
            source_type=ProvenanceEnvelope.AMAZON_OFFICIAL.value,
            required_role="brand_analytics",
            marketplace_supported=mp.supports_brand_analytics if mp else False,
            limitations=["Requires active Amazon Brand Registry enrollment"],
        ),
    ]

    # Non-Amazon / Free-First providers
    other_caps = [
        CapabilityEntry(
            id="macro_news_sentiment",
            name="GDELT 2.0 Doc Global News Intelligence",
            provider="gdelt",
            status=CapabilityStatus.AVAILABLE.value,
            source_type=ProvenanceEnvelope.PUBLIC_NEWS.value,
            required_role=None,
            marketplace_supported=True,
            limitations=["Public news REST API, zero API keys required"],
        ),
        CapabilityEntry(
            id="rss_feeds",
            name="Public Trade & Regulatory RSS Feeds",
            provider="rss_feeds",
            status=CapabilityStatus.AVAILABLE.value,
            source_type=ProvenanceEnvelope.PUBLIC_NEWS.value,
            required_role=None,
            marketplace_supported=True,
            limitations=["Public syndicate feeds parsed locally"],
        ),
        CapabilityEntry(
            id="structured_explanations",
            name="Local Ollama LLM Engine",
            provider="ollama",
            status=CapabilityStatus.AVAILABLE.value,
            source_type=ProvenanceEnvelope.MODELLED.value,
            required_role=None,
            marketplace_supported=True,
            limitations=["Local offline AI model execution"],
        ),
        CapabilityEntry(
            id="csv_ingestion",
            name="Seller CSV Data Uploads",
            provider="csv_provider",
            status=CapabilityStatus.AVAILABLE.value,
            source_type=ProvenanceEnvelope.SELLER_INPUT.value,
            required_role=None,
            marketplace_supported=True,
            limitations=["Manual spreadsheet upload adhering to defined schemas"],
        ),
        CapabilityEntry(
            id="synthetic_demo_data",
            name="Seeded Synthetic Evaluation Data",
            provider="demo_provider",
            status=CapabilityStatus.AVAILABLE.value,
            source_type=ProvenanceEnvelope.DEMO.value,
            required_role=None,
            marketplace_supported=True,
            limitations=["Deterministic synthetic data for evaluation"],
        ),
    ]

    return CapabilitiesResponse(capabilities=sp_caps + other_caps)


@router.post(
    "/connections/amazon/ingest",
    summary="Ingest authorized seller performance reports into database",
)
def ingest_amazon_report(
    req: IngestReportRequest,
    db_session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Ingests official Amazon SP-API report data (Sales & Traffic, FBA Inventory, or Listings Item)
    and persists facts into PostgreSQL / SQLite with AMAZON_OFFICIAL provenance.
    """
    adapter = get_amazon_sp_api_adapter(marketplace_id=req.marketplace_id or DEFAULT_MARKETPLACE_ID)

    report_type = req.report_type.strip()

    if report_type in ("GET_SALES_AND_TRAFFIC_REPORT", "sales_traffic"):
        metrics = adapter.ingest_sales_traffic(
            report_data=req.report_payload,
            session=db_session,
            default_product_id=req.product_id,
        )
        return {
            "status": "success",
            "report_type": "GET_SALES_AND_TRAFFIC_REPORT",
            "records_ingested": len(metrics),
            "provenance": ProvenanceEnvelope.AMAZON_OFFICIAL.value,
        }

    elif report_type in ("GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA", "fba_inventory", "inventory"):
        inv_results = adapter.ingest_inventory(
            report_data=req.report_payload,
            session=db_session,
            report_date=req.report_date,
        )
        return {
            "status": "success",
            "report_type": "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA",
            "records_ingested": len(inv_results),
            "provenance": ProvenanceEnvelope.AMAZON_OFFICIAL.value,
        }

    elif report_type in ("getListingsItem", "listings_item", "listing"):
        if not isinstance(req.report_payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listings item payload must be a JSON dictionary.",
            )
        listing = adapter.ingest_listing(
            item_data=req.report_payload,
            session=db_session,
        )
        return {
            "status": "success",
            "report_type": "getListingsItem",
            "product_id": listing.product_id,
            "title": listing.title,
            "provenance": ProvenanceEnvelope.AMAZON_OFFICIAL.value,
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report type: '{req.report_type}'",
        )
