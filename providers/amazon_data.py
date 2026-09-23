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
    """Amazon SP-API adapter boundary — NOT implemented. See module
    docstring. Reports unconfigured unless real credentials are present,
    and every data method raises NotImplementedError rather than a fake
    success even if credentials happen to be set, since the calls
    themselves have never been written or run."""

    name = "sp_api"

    def __init__(self) -> None:
        self._client_id = os.environ.get("AMAZON_SP_API_CLIENT_ID")
        self._client_secret = os.environ.get("AMAZON_SP_API_CLIENT_SECRET")
        self._refresh_token = os.environ.get("AMAZON_SP_API_REFRESH_TOKEN")

    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret and self._refresh_token)

    def get_listing(self, asin: str) -> dict:
        raise NotImplementedError(
            "SP-API is not implemented in this build. Use DemoDataProvider "
            "or CSVDataProvider, or implement this adapter against Amazon's "
            "current Listings Items / Catalog Items API schema first."
        )


def get_amazon_data_provider() -> AmazonDataProvider:
    if os.environ.get("ENABLE_SP_API", "false").lower() == "true":
        sp = SPAPIProvider()
        if sp.is_configured():
            return sp
    return DemoDataProvider()
