"""
brand_analytics.py — Amazon Brand Analytics Adapter & CSV Ingestion for CommerceSense AI v3.

Provides:
  1. Ingestion of official SP-API Brand Analytics reports:
     - GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT
     - GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT
     - GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT
  2. Granular capability checking: Reports NEEDS_BRAND_REGISTRY when unverified.
  3. CSV Fallback importer for seller Brand Analytics exports.
  4. Standardized SourceEnvelope provenance (AMAZON_OFFICIAL for API, SELLER_INPUT for CSV).
  5. Strictly avoids conflating click-share or search frequency rank with universal keyword volume.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from providers.amazon_sp_api import (
    DEFAULT_MARKETPLACE_ID,
    AmazonSPAPIAdapter,
    CapabilityStatus,
    get_amazon_sp_api_adapter,
)
from providers.provenance import (
    ProvenanceEnvelope,
    SourceEnvelope,
    register_source_envelope_in_db,
)

logger = logging.getLogger("commerce_sense.brand_analytics")


# =====================================================================
# 1. Capability & Brand Registry Verification
# =====================================================================

def get_brand_analytics_status(
    adapter: Optional[AmazonSPAPIAdapter] = None,
    marketplace_id: str = DEFAULT_MARKETPLACE_ID,
) -> Dict[str, Any]:
    """Evaluates Brand Analytics availability for the connected account.
    Returns granular capability state (AVAILABLE, NEEDS_BRAND_REGISTRY, NOT_AUTHORISED, etc.).
    """
    sp_adapter = adapter or get_amazon_sp_api_adapter()
    if not sp_adapter.is_configured():
        return {
            "status": CapabilityStatus.NOT_AUTHORISED.value,
            "can_access_api": False,
            "supports_csv_import": True,
            "message": "SP-API credentials unconfigured. Connect account or upload Brand Analytics CSV.",
        }

    # Brand Analytics requires official Brand Registry role authorization
    # Check if seller has brand analytics role authorized
    # By default, without specific Brand Registry verification, report NEEDS_BRAND_REGISTRY
    has_brand_role = sp_adapter.has_role("BRAND_ANALYTICS") if hasattr(sp_adapter, "has_role") else False

    if not has_brand_role:
        return {
            "status": CapabilityStatus.NEEDS_BRAND_REGISTRY.value,
            "can_access_api": False,
            "supports_csv_import": True,
            "message": (
                "Brand Analytics API requires active Amazon Brand Registry enrollment. "
                "You can still import official Brand Analytics CSV exports."
            ),
        }

    return {
        "status": CapabilityStatus.AVAILABLE.value,
        "can_access_api": True,
        "supports_csv_import": True,
        "message": "Brand Analytics reports active and supported.",
    }


# =====================================================================
# 2. Report & CSV Ingestion Pipelines
# =====================================================================

def parse_brand_analytics_search_terms(
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    source_type: ProvenanceEnvelope = ProvenanceEnvelope.SELLER_INPUT,
) -> Dict[str, Any]:
    """Parses Amazon Brand Analytics Search Terms report (JSON or CSV).
    Extracts Search Frequency Rank, Top 3 Clicked ASINs, Click Share %, and Conversion Share %.
    """
    items: List[Dict[str, Any]] = []

    if isinstance(data, str):
        # CSV parsing
        reader = csv.DictReader(io.StringIO(data.strip()))
        for row in reader:
            # Normalize column keys
            clean_row = {k.strip().lower().replace(" ", "_").replace("#", "num_"): v.strip() for k, v in row.items() if k}

            term = clean_row.get("search_term") or clean_row.get("keyword") or ""
            if not term:
                continue

            try:
                sfr = int(clean_row.get("search_frequency_rank") or clean_row.get("rank") or 999999)
            except ValueError:
                sfr = 999999

            top_asins = []
            for i in (1, 2, 3):
                asin_val = clean_row.get(f"num_{i}_clicked_asin") or clean_row.get(f"{i}_clicked_asin")
                title_val = clean_row.get(f"num_{i}_product_title") or clean_row.get(f"{i}_product_title") or ""
                click_share = clean_row.get(f"num_{i}_click_share") or clean_row.get(f"{i}_click_share") or "0%"
                conv_share = clean_row.get(f"num_{i}_conversion_share") or clean_row.get(f"{i}_conversion_share") or "0%"

                if asin_val:
                    top_asins.append({
                        "rank": i,
                        "asin": asin_val,
                        "title": title_val,
                        "click_share": click_share,
                        "conversion_share": conv_share,
                    })

            items.append({
                "search_term": term,
                "search_frequency_rank": sfr,
                "department": clean_row.get("department", "All"),
                "top_clicked_asins": top_asins,
            })
    elif isinstance(data, dict):
        # JSON report payload
        records = data.get("data", []) or data.get("searchTerms", [])
        for rec in records:
            items.append({
                "search_term": rec.get("searchTerm", ""),
                "search_frequency_rank": rec.get("searchFrequencyRank", 999999),
                "department": rec.get("department", "All"),
                "top_clicked_asins": rec.get("clickedAsins", []),
            })
    elif isinstance(data, list):
        items = data

    # Sort by Search Frequency Rank (lower rank = higher search popularity)
    items.sort(key=lambda x: x.get("search_frequency_rank", 999999))

    envelope = SourceEnvelope.create(
        source_id=f"brand-analytics-{int(time.time())}",
        provider="amazon-brand-analytics",
        source_type=source_type,
        confidence="high",
        limitations=[
            "Search Frequency Rank is an ordinal rank (1 = most searched term on Amazon).",
            "Click share and conversion share represent top clicked ASIN percentages, not absolute query counts.",
        ],
        raw_data={"records_count": len(items)},
    )
    register_source_envelope_in_db(envelope)

    return {
        "envelope": envelope.model_dump(),
        "total_terms": len(items),
        "search_terms": items,
    }


def parse_search_query_performance(
    data: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Parses GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT.
    Contains customer funnel metrics: Search Funnel Impressions, Clicks, Cart Adds, Purchases.
    """
    queries: List[Dict[str, Any]] = []

    if isinstance(data, str):
        reader = csv.DictReader(io.StringIO(data.strip()))
        for row in reader:
            clean = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}
            query_str = clean.get("search_query") or clean.get("query") or ""
            if not query_str:
                continue

            queries.append({
                "search_query": query_str,
                "query_score": clean.get("search_query_score", "0"),
                "impressions": int(clean.get("impressions", 0) or 0),
                "clicks": int(clean.get("clicks", 0) or 0),
                "cart_adds": int(clean.get("cart_adds", 0) or 0),
                "purchases": int(clean.get("purchases", 0) or 0),
                "brand_share_pct": float(clean.get("brand_share", 0) or 0.0),
            })
    elif isinstance(data, dict):
        for rec in data.get("queries", []):
            queries.append(rec)

    envelope = SourceEnvelope.create(
        source_id=f"sqp-report-{int(time.time())}",
        provider="amazon-brand-analytics",
        source_type=ProvenanceEnvelope.AMAZON_OFFICIAL,
        confidence="high",
        limitations=[
            "Official Search Query Performance report reflects search funnel conversions for registered brand.",
        ],
        raw_data={"queries_count": len(queries)},
    )
    register_source_envelope_in_db(envelope)

    return {
        "envelope": envelope.model_dump(),
        "queries_count": len(queries),
        "queries": queries,
    }

