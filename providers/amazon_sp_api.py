"""
amazon_sp_api.py — Official Amazon Selling Partner API (SP-API) Adapter for CommerceSense AI v3.

Provides:
  1. European Regional Endpoint (sellingpartnerapi-eu.amazon.com) for Amazon India (A21TJRUUN4KGV)
     and multi-region marketplace directory.
  2. Official Login with Amazon (LWA) token exchange with thread-safe in-memory caching
     and proactive expiry refresh.
  3. Shared per-operation token bucket rate limiter with Amazon usage plan limits
     and HTTP 429 backoff handling.
  4. Ingestion pipelines for:
     - GET_SALES_AND_TRAFFIC_REPORT
     - GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA
     - getListingsItem / Catalog items
  5. Persistence into PostgreSQL / SQLAlchemy models (daily_metrics, products, listing_data)
     with SourceEnvelope(ProvenanceEnvelope.AMAZON_OFFICIAL) provenance registration.
  6. Granular capability matrix (AVAILABLE, NEEDS_ROLE, NEEDS_BRAND_REGISTRY,
     MARKETPLACE_UNSUPPORTED, NOT_AUTHORISED, RATE_LIMITED).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import requests

from providers.gate import is_free_only_mode, validate_egress_url
from providers.provenance import (
    ProvenanceEnvelope,
    SourceEnvelope,
    register_source_envelope_in_db,
)

logger = logging.getLogger("commerce_sense.amazon_sp_api")


def _safe_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _safe_date(val: Any) -> str:
    """Extracts YYYY-MM-DD from an ISO timestamp or date string."""
    if not val:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s = str(val).strip()
    return s[:10] if len(s) >= 10 else s


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        s = str(val).replace(",", "").strip()
        return int(float(s)) if s else default
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        s = str(val).replace(",", "").strip()
        return float(s) if s else default
    except (ValueError, TypeError):
        return default


def _safe_decimal(val: Any, default: str = "0.00") -> Decimal:
    if val is None:
        return Decimal(default)
    try:
        s = str(val).replace(",", "").strip()
        return Decimal(s) if s else Decimal(default)
    except Exception:
        return Decimal(default)


# =====================================================================
# 1. Capability Status & Marketplace Configuration
# =====================================================================

class CapabilityStatus(str, Enum):
    """Granular operational status for each SP-API capability."""
    AVAILABLE = "AVAILABLE"
    NEEDS_ROLE = "NEEDS_ROLE"
    NEEDS_BRAND_REGISTRY = "NEEDS_BRAND_REGISTRY"
    MARKETPLACE_UNSUPPORTED = "MARKETPLACE_UNSUPPORTED"
    NOT_AUTHORISED = "NOT_AUTHORISED"
    RATE_LIMITED = "RATE_LIMITED"


@dataclass(frozen=True)
class AmazonMarketplace:
    marketplace_id: str
    country_code: str
    region: str  # "EU", "NA", "FE"
    endpoint: str
    currency: str
    name: str
    supports_brand_analytics: bool = True


# Canonical SP-API Marketplaces & Endpoints (docs/DATA_SOURCES.md §3.1)
# Note: Amazon India (Amazon.in) routes via the European regional endpoint.
MARKETPLACES: Dict[str, AmazonMarketplace] = {
    # Default Target: Amazon India
    "A21TJRUUN4KGV": AmazonMarketplace(
        marketplace_id="A21TJRUUN4KGV",
        country_code="IN",
        region="EU",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
        currency="INR",
        name="Amazon India (Amazon.in)",
        supports_brand_analytics=True,
    ),
    # North America
    "ATVPDKIKX0DER": AmazonMarketplace(
        marketplace_id="ATVPDKIKX0DER",
        country_code="US",
        region="NA",
        endpoint="https://sellingpartnerapi-na.amazon.com",
        currency="USD",
        name="Amazon US (Amazon.com)",
        supports_brand_analytics=True,
    ),
    "A2EUQ1WTGCTBG2": AmazonMarketplace(
        marketplace_id="A2EUQ1WTGCTBG2",
        country_code="CA",
        region="NA",
        endpoint="https://sellingpartnerapi-na.amazon.com",
        currency="CAD",
        name="Amazon Canada (Amazon.ca)",
        supports_brand_analytics=True,
    ),
    "A1AM78C64UM0Y8": AmazonMarketplace(
        marketplace_id="A1AM78C64UM0Y8",
        country_code="MX",
        region="NA",
        endpoint="https://sellingpartnerapi-na.amazon.com",
        currency="MXN",
        name="Amazon Mexico (Amazon.com.mx)",
        supports_brand_analytics=True,
    ),
    # Europe
    "A1F83G8C2ARO7P": AmazonMarketplace(
        marketplace_id="A1F83G8C2ARO7P",
        country_code="UK",
        region="EU",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
        currency="GBP",
        name="Amazon UK (Amazon.co.uk)",
        supports_brand_analytics=True,
    ),
    "A1PA6795UKMFR9": AmazonMarketplace(
        marketplace_id="A1PA6795UKMFR9",
        country_code="DE",
        region="EU",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
        currency="EUR",
        name="Amazon Germany (Amazon.de)",
        supports_brand_analytics=True,
    ),
    "A13V1IB3VIYZZH": AmazonMarketplace(
        marketplace_id="A13V1IB3VIYZZH",
        country_code="FR",
        region="EU",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
        currency="EUR",
        name="Amazon France (Amazon.fr)",
        supports_brand_analytics=True,
    ),
    "APJ6JRA9NG5V4": AmazonMarketplace(
        marketplace_id="APJ6JRA9NG5V4",
        country_code="IT",
        region="EU",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
        currency="EUR",
        name="Amazon Italy (Amazon.it)",
        supports_brand_analytics=True,
    ),
    "A1RKKUPIHCS9HS": AmazonMarketplace(
        marketplace_id="A1RKKUPIHCS9HS",
        country_code="ES",
        region="EU",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
        currency="EUR",
        name="Amazon Spain (Amazon.es)",
        supports_brand_analytics=True,
    ),
    # Far East
    "A1VC38T7YXB528": AmazonMarketplace(
        marketplace_id="A1VC38T7YXB528",
        country_code="JP",
        region="FE",
        endpoint="https://sellingpartnerapi-fe.amazon.com",
        currency="JPY",
        name="Amazon Japan (Amazon.co.jp)",
        supports_brand_analytics=True,
    ),
    "A39IBJ37TRP1C6": AmazonMarketplace(
        marketplace_id="A39IBJ37TRP1C6",
        country_code="AU",
        region="FE",
        endpoint="https://sellingpartnerapi-fe.amazon.com",
        currency="AUD",
        name="Amazon Australia (Amazon.com.au)",
        supports_brand_analytics=True,
    ),
    "A19VAU5U5O7RUS": AmazonMarketplace(
        marketplace_id="A19VAU5U5O7RUS",
        country_code="SG",
        region="FE",
        endpoint="https://sellingpartnerapi-fe.amazon.com",
        currency="SGD",
        name="Amazon Singapore (Amazon.sg)",
        supports_brand_analytics=False,  # e.g., Brand Analytics not active in SG
    ),
}

DEFAULT_MARKETPLACE_ID = "A21TJRUUN4KGV"


def get_marketplace(marketplace_id: str) -> Optional[AmazonMarketplace]:
    """Retrieves Amazon Marketplace metadata by ID, falling back to None if unsupported."""
    return MARKETPLACES.get(marketplace_id)


# =====================================================================
# 2. Token Bucket Rate Limiter with 429 Backoff
# =====================================================================

# Standard Amazon SP-API Usage Plans (requests per second, burst capacity)
STANDARD_USAGE_PLANS: Dict[str, Tuple[float, float]] = {
    # Reports API
    "create_report": (0.0167, 15.0),       # 1 req per min, burst 15
    "get_report": (2.0, 15.0),             # 2 req/s, burst 15
    "get_report_document": (0.0167, 15.0), # 1 req per min, burst 15
    # Catalog & Listings
    "get_listings_item": (5.0, 10.0),      # 5 req/s, burst 10
    # Inventory
    "get_inventory_summaries": (2.0, 5.0), # 2 req/s, burst 5
    # Product Pricing
    "get_competitive_pricing": (10.0, 20.0), # 10 req/s, burst 20
    # Default fallback
    "default": (1.0, 5.0),
}


class TokenBucketRateLimiter:
    """
    Shared, per-operation thread-safe token bucket rate limiter respecting
    official Amazon SP-API usage plans and HTTP 429 Retry-After backoff headers.
    """

    def __init__(self, plans: Optional[Dict[str, Tuple[float, float]]] = None):
        self._plans = plans or STANDARD_USAGE_PLANS
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _get_or_init_bucket(self, operation: str) -> Dict[str, Any]:
        if operation not in self._buckets:
            rate, burst = self._plans.get(operation, self._plans.get("default", (1.0, 5.0)))
            self._buckets[operation] = {
                "rate": float(rate),
                "burst": float(burst),
                "tokens": float(burst),
                "last_replenished": time.time(),
                "throttled_until": 0.0,
                "consecutive_throttles": 0,
            }
        return self._buckets[operation]

    def acquire(
        self,
        operation: str,
        tokens: float = 1.0,
        block: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Attempts to acquire the specified number of tokens for an operation.
        If block is True, waits up to timeout seconds if the bucket is empty or throttled.
        """
        start_time = time.time()

        while True:
            with self._lock:
                now = time.time()
                bucket = self._get_or_init_bucket(operation)

                # Check if bucket is under HTTP 429 throttle cooldown
                if now < bucket["throttled_until"]:
                    wait_throttled = bucket["throttled_until"] - now
                    if not block:
                        return False
                    if timeout is not None and (now - start_time + wait_throttled) > timeout:
                        return False
                    # Must wait for cooldown outside the lock
                    sleep_duration = wait_throttled
                else:
                    # Replenish tokens based on elapsed time
                    elapsed = max(0.0, now - bucket["last_replenished"])
                    bucket["tokens"] = min(
                        bucket["burst"],
                        bucket["tokens"] + (elapsed * bucket["rate"]),
                    )
                    bucket["last_replenished"] = now

                    # Check if enough tokens are available
                    if bucket["tokens"] >= tokens:
                        bucket["tokens"] -= tokens
                        return True

                    if not block:
                        return False

                    # Calculate wait time for tokens to accumulate
                    needed = tokens - bucket["tokens"]
                    wait_tokens = needed / bucket["rate"] if bucket["rate"] > 0 else 1.0
                    if timeout is not None and (now - start_time + wait_tokens) > timeout:
                        return False
                    sleep_duration = min(wait_tokens, 1.0)

            # Sleep outside the lock
            time.sleep(min(sleep_duration, 0.5))

    def record_throttle(
        self,
        operation: str,
        retry_after: Optional[float] = None,
        backoff_base: float = 2.0,
    ) -> float:
        """
        Records an HTTP 429 response from Amazon SP-API.
        Applies Retry-After header duration or exponential backoff with jitter.
        """
        with self._lock:
            now = time.time()
            bucket = self._get_or_init_bucket(operation)
            bucket["consecutive_throttles"] += 1

            if retry_after is not None and retry_after > 0:
                duration = float(retry_after)
            else:
                # Exponential backoff with jitter: min(60, (base ^ count) + jitter)
                exponent = min(bucket["consecutive_throttles"], 6)
                jitter = random.uniform(0.1, 0.5)
                duration = min(60.0, (backoff_base ** exponent) + jitter)

            bucket["throttled_until"] = now + duration
            # Empty remaining tokens during throttle
            bucket["tokens"] = 0.0
            bucket["last_replenished"] = now
            logger.warning(
                "SP-API throttled for operation '%s'. Backing off for %.2fs (consecutive: %d)",
                operation,
                duration,
                bucket["consecutive_throttles"],
            )
            return duration

    def on_success(self, operation: str) -> None:
        """Resets consecutive throttle counters on successful request."""
        with self._lock:
            if operation in self._buckets:
                self._buckets[operation]["consecutive_throttles"] = 0

    def is_rate_limited(self, operation: str) -> bool:
        """Checks if operation is currently throttled or lacking tokens."""
        with self._lock:
            now = time.time()
            bucket = self._get_or_init_bucket(operation)
            if now < bucket["throttled_until"]:
                return True
            elapsed = max(0.0, now - bucket["last_replenished"])
            available = min(bucket["burst"], bucket["tokens"] + (elapsed * bucket["rate"]))
            return available < 1.0

    def get_status(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Returns rate limiter operational metrics."""
        with self._lock:
            now = time.time()
            if operation:
                bucket = self._get_or_init_bucket(operation)
                elapsed = max(0.0, now - bucket["last_replenished"])
                tokens = min(bucket["burst"], bucket["tokens"] + (elapsed * bucket["rate"]))
                throttled = now < bucket["throttled_until"]
                return {
                    "operation": operation,
                    "available_tokens": round(tokens, 2),
                    "burst_capacity": bucket["burst"],
                    "rate_per_sec": bucket["rate"],
                    "is_throttled": throttled,
                    "throttled_remaining_sec": max(0.0, round(bucket["throttled_until"] - now, 2)) if throttled else 0.0,
                    "consecutive_throttles": bucket["consecutive_throttles"],
                }

            # Return aggregate for all tracked operations
            result = {}
            for op in list(self._plans.keys()):
                bucket = self._get_or_init_bucket(op)
                elapsed = max(0.0, now - bucket["last_replenished"])
                tokens = min(bucket["burst"], bucket["tokens"] + (elapsed * bucket["rate"]))
                throttled = now < bucket["throttled_until"]
                result[op] = {
                    "available_tokens": round(tokens, 2),
                    "burst_capacity": bucket["burst"],
                    "rate_per_sec": bucket["rate"],
                    "is_throttled": throttled,
                    "throttled_remaining_sec": max(0.0, round(bucket["throttled_until"] - now, 2)) if throttled else 0.0,
                }
            return result

    def reset(self, operation: Optional[str] = None) -> None:
        """Resets buckets for testing or system restart."""
        with self._lock:
            if operation:
                self._buckets.pop(operation, None)
            else:
                self._buckets.clear()


# Global shared rate limiter singleton
global_rate_limiter = TokenBucketRateLimiter()


# =====================================================================
# 3. Official Amazon LWA (Login with Amazon) Token Manager
# =====================================================================

class AmazonAuthenticationError(RuntimeError):
    """Raised when Amazon LWA token exchange or authentication fails."""
    pass


class LWATokenManager:
    """
    Manages Login with Amazon (LWA) OAuth 2.0 token lifecycle.
    Implements thread-safe in-memory caching and proactive expiry refresh
    (default: refreshes 300 seconds before token expires).
    """

    OAUTH_ENDPOINT = "https://api.amazon.com/auth/o2/token"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        oauth_endpoint: str = OAUTH_ENDPOINT,
        proactive_refresh_seconds: float = 300.0,
        transport_fn: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        self.client_id = client_id or os.environ.get("AMAZON_SP_API_CLIENT_ID") or os.environ.get("SP_API_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("AMAZON_SP_API_CLIENT_SECRET") or os.environ.get("SP_API_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.environ.get("AMAZON_SP_API_REFRESH_TOKEN") or os.environ.get("SP_API_REFRESH_TOKEN")
        self.oauth_endpoint = oauth_endpoint
        self.proactive_refresh_seconds = proactive_refresh_seconds
        self._transport_fn = transport_fn

        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._token_type: str = "bearer"
        self._lock = threading.Lock()

    def is_configured(self) -> bool:
        """Returns True if client credentials and refresh token are present."""
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def is_token_valid(self) -> bool:
        """Returns True if cached access token is valid and not nearing proactive refresh window."""
        with self._lock:
            return bool(
                self._access_token
                and (time.time() + self.proactive_refresh_seconds) < self._expires_at
            )

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieves a valid LWA access token from cache or exchanges the refresh token.
        Thread-safe double-checked locking ensures only one proactive exchange runs.
        """
        if not self.is_configured():
            raise AmazonAuthenticationError(
                "SP-API LWA credentials not configured. Set AMAZON_SP_API_CLIENT_ID, "
                "AMAZON_SP_API_CLIENT_SECRET, and AMAZON_SP_API_REFRESH_TOKEN."
            )

        if not force_refresh and self.is_token_valid():
            with self._lock:
                if self._access_token:
                    return self._access_token

        with self._lock:
            # Re-check after obtaining lock
            if not force_refresh and bool(
                self._access_token and (time.time() + self.proactive_refresh_seconds) < self._expires_at
            ):
                return self._access_token  # type: ignore

            # Perform OAuth token exchange
            token_data = self._exchange_token()
            self._access_token = token_data["access_token"]
            expires_in = float(token_data.get("expires_in", 3600.0))
            self._expires_at = time.time() + expires_in
            self._token_type = token_data.get("token_type", "bearer")
            logger.info("Successfully refreshed Amazon LWA access token. Valid for %.0f seconds.", expires_in)
            return self._access_token

    def get_lwa_access_token(self) -> str:
        """Alias conforming to official amzn-sp-api SDK AccessTokenCache protocol."""
        return self.get_access_token()

    def _exchange_token(self) -> Dict[str, Any]:
        """Calls the Amazon OAuth 2.0 token endpoint to obtain a fresh access token."""
        validate_egress_url(self.oauth_endpoint)

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }

        # Support custom transport for offline tests
        if self._transport_fn:
            return self._transport_fn(self.oauth_endpoint, payload)

        try:
            resp = requests.post(
                self.oauth_endpoint,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                timeout=10.0,
            )
            if resp.status_code == 400 or resp.status_code == 401:
                raise AmazonAuthenticationError(
                    f"Amazon LWA authentication rejected ({resp.status_code}): {resp.text}"
                )
            resp.raise_for_status()
            data = resp.json()
            if "access_token" not in data:
                raise AmazonAuthenticationError(f"Missing access_token in LWA response: {data}")
            return data
        except requests.RequestException as exc:
            raise AmazonAuthenticationError(f"Failed to communicate with Amazon LWA endpoint: {exc}") from exc

    def set_cached_token(self, token: str, expires_in: float) -> None:
        """Utility for test fixtures to populate the cache directly."""
        with self._lock:
            self._access_token = token
            self._expires_at = time.time() + expires_in

    def clear_cache(self) -> None:
        """Clears cached token."""
        with self._lock:
            self._access_token = None
            self._expires_at = 0.0

    @property
    def masked_client_id(self) -> Optional[str]:
        """Returns security-safe masked client identifier (never reveals secret)."""
        if not self.client_id:
            return None
        if len(self.client_id) <= 8:
            return "****"
        return f"{self.client_id[:4]}...{self.client_id[-4:]}"

    def get_token_status(self) -> Dict[str, Any]:
        """Returns non-sensitive token cache diagnostics."""
        with self._lock:
            now = time.time()
            remaining = max(0.0, self._expires_at - now) if self._access_token else 0.0
            return {
                "cached": bool(self._access_token),
                "is_valid": bool(self._access_token and (now + self.proactive_refresh_seconds) < self._expires_at),
                "expires_in_seconds": round(remaining, 1) if self._access_token else None,
                "proactive_refresh_threshold_seconds": self.proactive_refresh_seconds,
            }


# =====================================================================
# 4. Report Parsing & Normalization Engine
# =====================================================================

def parse_sales_and_traffic_report(data: Union[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parses Amazon SP-API GET_SALES_AND_TRAFFIC_REPORT JSON documents.
    Extracts ordered sales amount, units ordered, total orders, sessions,
    page views, and Buy Box percentage. Supports both daily aggregate and per-ASIN breakdowns.
    """
    if isinstance(data, str):
        if not data.strip():
            return []
        data = json.loads(data)

    if not isinstance(data, dict):
        return []

    records: List[Dict[str, Any]] = []

    # 1. Parse per-ASIN daily records if present
    asins_data = data.get("salesAndTrafficByAsin") or []
    if asins_data:
        rep_spec = data.get("reportSpecification") or {}
        raw_date = (
            rep_spec.get("dataEndTime")
            or rep_spec.get("dataStartTime")
            or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        report_date = _safe_date(raw_date)

        for entry in asins_data:
            if not isinstance(entry, dict):
                continue
            sales = entry.get("salesByAsin") or {}
            traffic = entry.get("trafficByAsin") or {}
            ordered_sales = sales.get("orderedProductSales") or {}

            records.append({
                "date": report_date,
                "sku": entry.get("sku"),
                "asin": entry.get("childAsin") or entry.get("parentAsin"),
                "units_sold": _safe_int(sales.get("unitsOrdered"), 0),
                "total_orders": _safe_int(sales.get("totalOrderItems"), 0),
                "ordered_sales": _safe_decimal(ordered_sales.get("amount"), "0.00"),
                "currency": ordered_sales.get("currencyCode") or "INR",
                "sessions": _safe_int(traffic.get("sessions"), 0),
                "page_views": _safe_int(traffic.get("pageViews"), 0),
                "buy_box_percentage": _safe_float(traffic.get("buyBoxPercentage"), 0.0),
            })
        return records

    # 2. Parse date-based aggregates (salesAndTrafficByDate)
    dates_data = data.get("salesAndTrafficByDate") or []
    for entry in dates_data:
        if not isinstance(entry, dict):
            continue
        date_str = _safe_date(entry.get("date"))
        sales = entry.get("salesByDate") or {}
        traffic = entry.get("trafficByDate") or {}
        ordered_sales = sales.get("orderedProductSales") or {}

        records.append({
            "date": date_str,
            "sku": None,
            "asin": None,
            "units_sold": _safe_int(sales.get("unitsOrdered"), 0),
            "total_orders": _safe_int(sales.get("totalOrderItems"), 0),
            "ordered_sales": _safe_decimal(ordered_sales.get("amount"), "0.00"),
            "currency": ordered_sales.get("currencyCode") or "INR",
            "sessions": _safe_int(traffic.get("sessions"), 0),
            "page_views": _safe_int(traffic.get("pageViews"), 0),
            "buy_box_percentage": _safe_float(traffic.get("buyBoxPercentage"), 0.0),
        })

    return records


def parse_fba_inventory_report(
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Parses Amazon SP-API GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA flat files (TSV)
    or JSON summaries from the FbaInventoryApi.
    Extracts SKU, ASIN, fulfillable units, reserved units, and condition.
    """
    records: List[Dict[str, Any]] = []

    # Handle JSON summary format (e.g. from FbaInventoryApi.get_inventory_summaries)
    if isinstance(data, dict):
        payload = data.get("payload") or {}
        summaries = (
            data.get("inventorySummaries")
            or (payload.get("inventorySummaries") if isinstance(payload, dict) else [])
            or []
        )
        for item in summaries:
            if not isinstance(item, dict):
                continue
            details = item.get("inventoryDetails") or {}
            reserved_dict = details.get("reservedQuantity") or {}
            unfulfillable_dict = details.get("unfulfillableQuantity") or {}

            fulfillable = _safe_int(details.get("fulfillableQuantity"), 0)
            reserved = _safe_int(reserved_dict.get("totalReservedQuantity"), 0)
            unsellable = _safe_int(unfulfillable_dict.get("totalUnfulfillableQuantity"), 0)
            total = _safe_int(item.get("totalQuantity"), fulfillable + reserved + unsellable)

            records.append({
                "sku": item.get("sellerSku"),
                "asin": item.get("asin"),
                "product_name": item.get("productName"),
                "fulfillable_quantity": fulfillable,
                "reserved_quantity": reserved,
                "unsellable_quantity": unsellable,
                "total_quantity": total,
                "condition": item.get("condition") or "New",
            })
        return records

    if isinstance(data, list):
        return data

    if not isinstance(data, str) or not data.strip():
        return records

    # Handle TSV flat file format with case and delimiter normalization
    reader = csv.DictReader(io.StringIO(data), delimiter="\t")
    for row in reader:
        if not row:
            continue
        # Normalize row keys: lowercase, stripped, replace '-' and ' ' with '_'
        norm_row = {
            k.strip().lower().replace("-", "_").replace(" ", "_"): v
            for k, v in row.items()
            if k is not None
        }

        sku = norm_row.get("sku") or norm_row.get("seller_sku") or norm_row.get("merchant_sku")
        asin = norm_row.get("asin")
        product_name = (
            norm_row.get("product_name")
            or norm_row.get("item_name")
            or norm_row.get("title")
        )

        fulfillable = _safe_int(
            norm_row.get("afn_fulfillable_quantity")
            or norm_row.get("quantity_available")
            or norm_row.get("fulfillable_quantity")
            or 0
        )
        reserved = _safe_int(
            norm_row.get("afn_reserved_quantity")
            or norm_row.get("reserved_quantity")
            or 0
        )
        unsellable = _safe_int(
            norm_row.get("afn_unsellable_quantity")
            or norm_row.get("unsellable_quantity")
            or 0
        )
        total = _safe_int(
            norm_row.get("afn_total_quantity")
            or norm_row.get("total_quantity")
            or (fulfillable + reserved + unsellable)
        )

        records.append({
            "sku": sku,
            "asin": asin,
            "product_name": product_name,
            "fulfillable_quantity": fulfillable,
            "reserved_quantity": reserved,
            "unsellable_quantity": unsellable,
            "total_quantity": total,
            "condition": norm_row.get("condition") or "New",
        })

    return records


def parse_listings_item(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses Amazon SP-API getListingsItem response payload.
    Extracts SKU, ASIN, title, brand, product type, bullets, description, and images.
    """
    if not isinstance(data, dict):
        raise ValueError("Listings item payload must be a dictionary")

    # Unpack payload envelope if present
    if "payload" in data and isinstance(data["payload"], dict):
        data = data["payload"]

    sku = data.get("sku")
    summaries = data.get("summaries") or []
    summary = summaries[0] if summaries and isinstance(summaries[0], dict) else {}
    asin = summary.get("asin")
    product_type = summary.get("productType", "General")
    status = summary.get("status", ["ACTIVE"])
    if isinstance(status, list):
        status_str = "ACTIVE" if any(s in ("BUYABLE", "DISCOVERABLE", "ACTIVE") for s in status) else "INACTIVE"
    else:
        status_str = str(status)

    attributes = data.get("attributes") or {}

    # Extract title
    title = summary.get("itemName")
    if not title and "item_name" in attributes:
        item_names = attributes["item_name"]
        if isinstance(item_names, list) and item_names:
            if isinstance(item_names[0], dict):
                title = item_names[0].get("value")
            elif isinstance(item_names[0], str):
                title = item_names[0]
        elif isinstance(item_names, str):
            title = item_names
    title = title or (f"Amazon Product {sku}" if sku else "Amazon Product")

    # Extract brand
    brand = "Unknown Brand"
    if "brand" in attributes:
        brand_attrs = attributes["brand"]
        if isinstance(brand_attrs, list) and brand_attrs:
            if isinstance(brand_attrs[0], dict):
                brand = brand_attrs[0].get("value", brand)
            elif isinstance(brand_attrs[0], str):
                brand = brand_attrs[0]
        elif isinstance(brand_attrs, dict):
            brand = brand_attrs.get("value", brand)
        elif isinstance(brand_attrs, str):
            brand = brand_attrs

    # Extract bullets
    bullets: List[str] = []
    bullet_key = None
    for k in ("bullet_point", "bullet_points", "bulletPoints"):
        if k in attributes:
            bullet_key = k
            break
    if bullet_key:
        bp_list = attributes[bullet_key]
        if isinstance(bp_list, list):
            for bp in bp_list:
                if isinstance(bp, dict) and "value" in bp:
                    bullets.append(str(bp["value"]))
                elif isinstance(bp, str):
                    bullets.append(bp)
        elif isinstance(bp_list, str):
            bullets.append(bp_list)

    # Extract description
    description = ""
    for dk in ("product_description", "description"):
        if dk in attributes:
            desc_list = attributes[dk]
            if isinstance(desc_list, list) and desc_list:
                description = desc_list[0].get("value", "") if isinstance(desc_list[0], dict) else str(desc_list[0])
            elif isinstance(desc_list, dict):
                description = desc_list.get("value", "")
            elif isinstance(desc_list, str):
                description = desc_list
            break

    # Extract image URLs
    images: List[str] = []
    main_img = summary.get("mainImage") or {}
    if isinstance(main_img, dict) and main_img.get("link"):
        images.append(main_img["link"])
    for ik in ("main_product_image_locator", "other_product_image_locator_1", "images"):
        if ik in attributes:
            locators = attributes[ik]
            if isinstance(locators, list):
                for loc in locators:
                    if isinstance(loc, dict) and "media_location" in loc:
                        images.append(loc["media_location"])
                    elif isinstance(loc, str):
                        images.append(loc)

    return {
        "sku": sku,
        "asin": asin,
        "title": title,
        "brand": brand,
        "product_type": product_type,
        "bullets": bullets,
        "description": description,
        "image_urls": images,
        "image_count": len(images),
        "status": status_str,
        "raw_attributes": attributes,
    }


# =====================================================================
# 5. Database Persistence Pipeline (with SourceEnvelope Provenance)
# =====================================================================

def ingest_sales_and_traffic_report(
    report_data: Union[str, Dict[str, Any]],
    session: Any,
    marketplace_id: str = DEFAULT_MARKETPLACE_ID,
    default_product_id: Optional[str] = None,
) -> List[Any]:
    """
    Ingests GET_SALES_AND_TRAFFIC_REPORT records into SQLAlchemy DailyMetric models.
    Persists SourceEnvelope with AMAZON_OFFICIAL provenance into provenance_registry.
    """
    from db.models import DailyMetric, Product

    records = parse_sales_and_traffic_report(report_data)
    persisted_metrics: List[DailyMetric] = []

    for rec in records:
        sku = rec.get("sku") or default_product_id
        asin = rec.get("asin")
        date_str = _safe_date(rec["date"])

        # Determine target product identifier without clobbering unrelated products
        target_product_id = sku
        if not target_product_id:
            if asin:
                matched_prod = session.query(Product).filter_by(asin=asin).first()
                if matched_prod:
                    target_product_id = matched_prod.product_id
                else:
                    # Discrete new product keyed by its Amazon ASIN
                    target_product_id = asin
            else:
                first_prod = session.query(Product).first()
                target_product_id = first_prod.product_id if first_prod else "P001"

        # Ensure product exists
        prod = session.query(Product).filter_by(product_id=target_product_id).first()
        if not prod:
            prod = Product(
                product_id=target_product_id,
                asin=asin or "B00EXAMPLE",
                name=f"Amazon Product {target_product_id}",
                category="General",
                base_price=Decimal("499.00"),
                currency=rec.get("currency", "INR"),
            )
            session.add(prod)
            session.flush()

        # Upsert daily_metric
        metric = session.query(DailyMetric).filter_by(
            product_id=target_product_id,
            date=date_str,
        ).first()

        has_buy_box = bool(rec.get("buy_box_percentage", 0.0) >= 50.0)

        if not metric:
            metric = DailyMetric(
                product_id=target_product_id,
                date=date_str,
                units_sold=rec["units_sold"],
                inventory_level=0,
                rank=0,
                has_buy_box=has_buy_box,
                ad_spend=Decimal("0.0000"),
                ad_clicks=0,
                ad_sales=rec["ordered_sales"],
            )
            session.add(metric)
        else:
            metric.units_sold = rec["units_sold"]
            metric.has_buy_box = has_buy_box
            if rec["ordered_sales"] > 0:
                metric.ad_sales = rec["ordered_sales"]

        session.flush()
        persisted_metrics.append(metric)

        # Register official Amazon provenance envelope
        envelope = SourceEnvelope.create(
            source_id=f"amzn-sp-api:sales_traffic:{target_product_id}:{date_str}",
            provider="amzn-sp-api",
            source_type=ProvenanceEnvelope.AMAZON_OFFICIAL,
            raw_data=rec,
            marketplace_id=marketplace_id,
            currency=rec.get("currency", "INR"),
            confidence="high",
            limitations=["Official SP-API daily performance data from Amazon Selling Partner API"],
        )
        register_source_envelope_in_db(envelope, session)

    return persisted_metrics


def ingest_fba_inventory_report(
    report_data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    session: Any,
    report_date: Optional[str] = None,
    marketplace_id: str = DEFAULT_MARKETPLACE_ID,
) -> List[Dict[str, Any]]:
    """
    Ingests FBA inventory summaries into DailyMetric.inventory_level and updates Product.asin.
    Persists SourceEnvelope with AMAZON_OFFICIAL provenance.
    """
    from db.models import DailyMetric, Product

    date_str = _safe_date(report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    items = parse_fba_inventory_report(report_data)
    ingested_results: List[Dict[str, Any]] = []

    for item in items:
        sku = item.get("sku")
        asin = item.get("asin")
        fulfillable = int(item.get("fulfillable_quantity", 0))

        if not sku and not asin:
            continue

        target_sku = sku or asin

        # Find existing product by SKU or ASIN
        prod = session.query(Product).filter_by(product_id=target_sku).first()
        if not prod and asin:
            prod = session.query(Product).filter_by(asin=asin).first()

        if not prod:
            prod = Product(
                product_id=target_sku,
                asin=asin or "B00EXAMPLE",
                name=item.get("product_name") or f"Product {target_sku}",
                category="General",
                base_price=Decimal("499.00"),
                currency="INR",
            )
            session.add(prod)
            session.flush()
        elif asin and not prod.asin:
            prod.asin = asin

        actual_product_id = prod.product_id

        # Upsert inventory level in DailyMetric for report date
        metric = session.query(DailyMetric).filter_by(
            product_id=actual_product_id,
            date=date_str,
        ).first()

        if not metric:
            metric = DailyMetric(
                product_id=actual_product_id,
                date=date_str,
                units_sold=0,
                inventory_level=fulfillable,
                rank=0,
                has_buy_box=True,
                ad_spend=Decimal("0.0000"),
                ad_clicks=0,
                ad_sales=Decimal("0.0000"),
            )
            session.add(metric)
        else:
            metric.inventory_level = fulfillable

        session.flush()

        envelope = SourceEnvelope.create(
            source_id=f"amzn-sp-api:inventory:{actual_product_id}:{date_str}",
            provider="amzn-sp-api",
            source_type=ProvenanceEnvelope.AMAZON_OFFICIAL,
            raw_data=item,
            marketplace_id=marketplace_id,
            currency="INR",
            confidence="high",
            limitations=["Official real-time FBA inventory fulfillable count"],
        )
        register_source_envelope_in_db(envelope, session)
        ingested_results.append({
            "product_id": actual_product_id,
            "asin": asin,
            "fulfillable_quantity": fulfillable,
            "date": date_str,
        })

    return ingested_results


def ingest_listings_item(
    item_data: Dict[str, Any],
    session: Any,
    marketplace_id: str = DEFAULT_MARKETPLACE_ID,
) -> Any:
    """
    Ingests SP-API getListingsItem payload into Product catalog and ListingData tables.
    Persists SourceEnvelope with AMAZON_OFFICIAL provenance.
    """
    from db.models import ListingData, Product

    parsed = parse_listings_item(item_data)
    sku = parsed["sku"]
    if not sku:
        raise ValueError("Missing SKU in listings item data")

    # Upsert Product
    prod = session.query(Product).filter_by(product_id=sku).first()
    if not prod:
        prod = Product(
            product_id=sku,
            asin=parsed.get("asin"),
            name=parsed["title"],
            category=parsed["product_type"],
            base_price=Decimal("499.00"),
            currency="INR",
        )
        session.add(prod)
        session.flush()
    else:
        prod.name = parsed["title"]
        if parsed.get("asin"):
            prod.asin = parsed["asin"]

    # Upsert ListingData
    listing = session.query(ListingData).filter_by(product_id=sku).first()
    if not listing:
        listing = ListingData(
            product_id=sku,
            title=parsed["title"],
            brand=parsed["brand"],
            product_type=parsed["product_type"],
            bullets=parsed["bullets"],
            description=parsed["description"],
            backend_keywords="",
            attributes=parsed.get("raw_attributes", {}),
            image_urls=parsed["image_urls"],
            image_count=parsed["image_count"],
            listing_status=parsed["status"],
        )
        session.add(listing)
    else:
        listing.title = parsed["title"]
        listing.brand = parsed["brand"]
        listing.product_type = parsed["product_type"]
        listing.bullets = parsed["bullets"]
        listing.description = parsed["description"]
        listing.attributes = parsed.get("raw_attributes", {})
        listing.image_urls = parsed["image_urls"]
        listing.image_count = parsed["image_count"]
        listing.listing_status = parsed["status"]

    session.flush()

    envelope = SourceEnvelope.create(
        source_id=f"amzn-sp-api:listing:{sku}",
        provider="amzn-sp-api",
        source_type=ProvenanceEnvelope.AMAZON_OFFICIAL,
        raw_data=item_data,
        marketplace_id=marketplace_id,
        confidence="high",
        limitations=["Official catalog listings item data retrieved from Amazon SP-API"],
    )
    register_source_envelope_in_db(envelope, session)

    return listing


# =====================================================================
# 6. Isolated Amazon SP-API Adapter
# =====================================================================

class AmazonSPAPIAdapter:
    """
    Isolated adapter connecting CommerceSense AI v3 to the official Amazon SP-API SDK.
    Supports European regional routing for Amazon India, proactive LWA token caching,
    token bucket rate limiting, and capability evaluation.
    """

    name = "amzn-sp-api"

    def __init__(
        self,
        marketplace_id: str = DEFAULT_MARKETPLACE_ID,
        rate_limiter: Optional[TokenBucketRateLimiter] = None,
        token_manager: Optional[LWATokenManager] = None,
        has_brand_registry: Optional[bool] = None,
        granted_roles: Optional[List[str]] = None,
    ):
        self.marketplace_id = marketplace_id
        self.marketplace = get_marketplace(marketplace_id)
        self.is_marketplace_supported = self.marketplace is not None
        self._effective_marketplace = self.marketplace or MARKETPLACES[DEFAULT_MARKETPLACE_ID]
        self.rate_limiter = rate_limiter or global_rate_limiter
        self.token_manager = token_manager or LWATokenManager()

        # Developer account capability configuration
        self.has_brand_registry = (
            has_brand_registry
            if has_brand_registry is not None
            else os.environ.get("AMAZON_HAS_BRAND_REGISTRY", "false").lower() == "true"
        )
        self.granted_roles = set(
            granted_roles
            or os.environ.get("AMAZON_SP_API_ROLES", "pricing,reports,inventory,listings").lower().split(",")
        )

        self._api_client = None

    def is_configured(self) -> bool:
        """Checks whether Amazon SP-API credentials are fully configured."""
        return self.token_manager.is_configured()

    def get_api_client(self) -> Any:
        """
        Initializes an amzn-sp-api SDK ApiClient using the European regional endpoint
        (or configured marketplace endpoint) and our thread-safe LWATokenManager.
        """
        if not self.is_configured():
            raise AmazonAuthenticationError("Amazon SP-API credentials are not configured.")

        if self._api_client is None:
            from spapi.api_client import ApiClient
            from spapi.configuration import Configuration

            config = Configuration()
            config.host = self._effective_marketplace.endpoint
            config.access_token_cache = self.token_manager
            self._api_client = ApiClient(configuration=config)
        return self._api_client

    def get_sp_client(self) -> Any:
        """Returns API client instance for amzn-sp-api SDK."""
        return self.get_api_client()

    def get_reports_api(self) -> Any:
        """Returns official ReportsApi instance."""
        from spapi import ReportsApi
        return ReportsApi(api_client=self.get_api_client())

    def get_inventory_api(self) -> Any:
        """Returns official FbaInventoryApi instance."""
        from spapi import FbaInventoryApi
        return FbaInventoryApi(api_client=self.get_api_client())

    def get_listings_api(self) -> Any:
        """Returns official ListingsApi instance."""
        from spapi import ListingsApi
        return ListingsApi(api_client=self.get_api_client())

    def get_pricing_api(self) -> Any:
        """Returns official ProductPricingApi instance."""
        from spapi import ProductPricingApi
        return ProductPricingApi(api_client=self.get_api_client())

    def get_capability_status(self, capability: str) -> CapabilityStatus:
        """
        Computes granular capability status for the specified SP-API report or operation.
        Order of evaluation:
          1. Marketplace support (static platform constraint)
          2. Basic credentials authorization
          3. Brand Registry prerequisite
          4. Developer account roles
          5. Dynamic rate limiting
        """
        known_capabilities = {
            "sales_traffic_reports",
            "inventory_summaries",
            "listings_items",
            "competitive_pricing",
            "brand_analytics",
        }
        if capability not in known_capabilities:
            return CapabilityStatus.MARKETPLACE_UNSUPPORTED

        # 1. Check Marketplace validity and feature support
        if not self.is_marketplace_supported:
            return CapabilityStatus.MARKETPLACE_UNSUPPORTED

        if capability == "brand_analytics" and self.marketplace and not self.marketplace.supports_brand_analytics:
            return CapabilityStatus.MARKETPLACE_UNSUPPORTED

        # 2. Check basic authorization credentials
        if not self.is_configured():
            return CapabilityStatus.NOT_AUTHORISED

        # 3. Check Brand Registry requirement
        if capability == "brand_analytics" and not self.has_brand_registry:
            return CapabilityStatus.NEEDS_BRAND_REGISTRY

        # 4. Check Developer Role permissions
        required_role_map = {
            "sales_traffic_reports": "reports",
            "inventory_summaries": "inventory",
            "listings_items": "listings",
            "competitive_pricing": "pricing",
            "brand_analytics": "brand_analytics",
        }
        req_role = required_role_map.get(capability)
        if req_role and req_role not in self.granted_roles:
            return CapabilityStatus.NEEDS_ROLE

        # 5. Check dynamic rate limiting
        operation_map = {
            "sales_traffic_reports": "get_report",
            "inventory_summaries": "get_inventory_summaries",
            "listings_items": "get_listings_item",
            "competitive_pricing": "get_competitive_pricing",
            "brand_analytics": "create_report",
        }
        op_name = operation_map.get(capability, "default")
        if self.rate_limiter.is_rate_limited(op_name):
            return CapabilityStatus.RATE_LIMITED

        return CapabilityStatus.AVAILABLE

    def get_capabilities_matrix(self) -> Dict[str, str]:
        """Returns status map across all SP-API capabilities."""
        capabilities = [
            "sales_traffic_reports",
            "inventory_summaries",
            "listings_items",
            "competitive_pricing",
            "brand_analytics",
        ]
        return {cap: self.get_capability_status(cap).value for cap in capabilities}

    def get_connection_diagnostics(self) -> Dict[str, Any]:
        """Provides comprehensive, safe diagnostic information for GET /api/v1/connections/amazon."""
        configured = self.is_configured()
        token_status = self.token_manager.get_token_status()
        capabilities = self.get_capabilities_matrix()

        # Connection status summary
        if not self.is_marketplace_supported:
            overall_status = CapabilityStatus.MARKETPLACE_UNSUPPORTED.value
            connected = False
        elif not configured:
            overall_status = CapabilityStatus.NOT_AUTHORISED.value
            connected = False
        elif any(v == CapabilityStatus.RATE_LIMITED.value for v in capabilities.values()):
            overall_status = CapabilityStatus.RATE_LIMITED.value
            connected = True
        elif all(v == CapabilityStatus.AVAILABLE.value for v in capabilities.values()):
            overall_status = CapabilityStatus.AVAILABLE.value
            connected = True
        else:
            overall_status = "PARTIAL_ACCESS"
            connected = True

        mp = self.marketplace or AmazonMarketplace(
            marketplace_id=self.marketplace_id,
            country_code="UN",
            region="UNKNOWN",
            endpoint="UNKNOWN",
            currency="USD",
            name=f"Unsupported Marketplace ({self.marketplace_id})",
            supports_brand_analytics=False,
        )

        return {
            "connected": connected,
            "status": overall_status,
            "marketplace": {
                "marketplace_id": mp.marketplace_id,
                "country_code": mp.country_code,
                "name": mp.name,
                "region": mp.region,
                "endpoint": mp.endpoint,
                "currency": mp.currency,
            },
            "credentials_configured": configured,
            "client_id_masked": self.token_manager.masked_client_id,
            "token": token_status,
            "capabilities": capabilities,
            "rate_limits": self.rate_limiter.get_status(),
            "has_brand_registry": self.has_brand_registry,
            "granted_roles": sorted(list(self.granted_roles)),
            "provenance": {
                "provider": "amzn-sp-api",
                "source_type": ProvenanceEnvelope.AMAZON_OFFICIAL.value,
            },
        }

    # Data ingestion helpers
    def ingest_sales_traffic(
        self,
        report_data: Union[str, Dict[str, Any]],
        session: Any,
        default_product_id: Optional[str] = None,
    ) -> List[Any]:
        self.rate_limiter.acquire("get_report")
        return ingest_sales_and_traffic_report(
            report_data=report_data,
            session=session,
            marketplace_id=self._effective_marketplace.marketplace_id,
            default_product_id=default_product_id,
        )

    def ingest_inventory(
        self,
        report_data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        session: Any,
        report_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.rate_limiter.acquire("get_inventory_summaries")
        return ingest_fba_inventory_report(
            report_data=report_data,
            session=session,
            report_date=report_date,
            marketplace_id=self._effective_marketplace.marketplace_id,
        )

    def ingest_listing(
        self,
        item_data: Dict[str, Any],
        session: Any,
    ) -> Any:
        self.rate_limiter.acquire("get_listings_item")
        return ingest_listings_item(
            item_data=item_data,
            session=session,
            marketplace_id=self._effective_marketplace.marketplace_id,
        )


def get_amazon_sp_api_adapter(marketplace_id: str = DEFAULT_MARKETPLACE_ID) -> AmazonSPAPIAdapter:
    """Factory creating an AmazonSPAPIAdapter instance for the specified marketplace."""
    return AmazonSPAPIAdapter(marketplace_id=marketplace_id)
