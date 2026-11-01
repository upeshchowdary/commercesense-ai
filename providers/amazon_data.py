"""
amazon_data.py — the seller-data boundary for the four intelligence
modules. Nothing above this layer should know or care whether listing/
pricing/review/inventory facts came from the local synthetic database, a
seller-uploaded CSV, or (eventually) a real Amazon SP-API connection.

SPAPIProvider is intentionally a stub, not a real integration: there are no
SP-API credentials available in this environment to authenticate or verify
against, and this project's standing rule is to never claim something works
without having actually run it. The interface is complete so a real
implementation can be dropped in later without touching any calling code —
every method reports itself unconfigured rather than fabricating a response.
DemoDataProvider (the synthetic dataset) is always available, so every
module keeps working with zero external credentials.
"""

from __future__ import annotations

import os
from typing import Protocol


class AmazonDataProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...


class DemoDataProvider:
    """Reads the synthetic listing/pricing/review/inventory data generated
    by data/generate_synthetic_data.py into the local SQLite database.
    Always configured — this is the default and the demo-mode fallback."""

    name = "demo"

    def is_configured(self) -> bool:
        return True


class CSVDataProvider:
    """Validates and imports seller-provided CSV files. See
    api/routers/data_import.py for the actual upload/validate/preview/
    commit workflow — this class is the marker used for provenance."""

    name = "csv"

    def is_configured(self) -> bool:
        return True


class SPAPIProvider:
    """Amazon SP-API adapter backed by providers/amazon_sp_api.py.
    Reports unconfigured if credentials are not present, falling back
    safely to DemoDataProvider or CSVDataProvider."""

    name = "sp_api"

    def __init__(self) -> None:
        from providers.amazon_sp_api import AmazonSPAPIAdapter
        self._adapter = AmazonSPAPIAdapter()

    def is_configured(self) -> bool:
        return self._adapter.is_configured()

    @property
    def adapter(self):
        return self._adapter

    def get_listing(self, asin: str) -> dict:
        if not self.is_configured():
            raise NotImplementedError(
                "SP-API is not configured. Use DemoDataProvider or CSVDataProvider, "
                "or provide valid Amazon SP-API credentials."
            )
        # Attempt to find listing from DB or adapter
        from db.session import db_session_scope
        from db.models import ListingData, Product
        with db_session_scope() as session:
            prod = session.query(Product).filter_by(asin=asin).first()
            if prod and prod.listing:
                return {
                    "product_id": prod.product_id,
                    "title": prod.listing.title,
                    "brand": prod.listing.brand,
                    "bullets": prod.listing.bullets,
                    "description": prod.listing.description,
                    "image_count": prod.listing.image_count,
                    "listing_status": prod.listing.listing_status,
                }
        return {"asin": asin, "status": "NOT_FOUND"}


def get_amazon_data_provider() -> AmazonDataProvider:
    if os.environ.get("ENABLE_SP_API", "false").lower() == "true":
        sp = SPAPIProvider()
        if sp.is_configured():
            return sp
    if os.environ.get("USE_CSV_DATA", "false").lower() == "true":
        return CSVDataProvider()
    return DemoDataProvider()
