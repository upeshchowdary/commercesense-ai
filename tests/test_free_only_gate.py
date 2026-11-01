"""
test_free_only_gate.py — Tests for FREE_ONLY hard gate and egress filter.
"""

from __future__ import annotations

import os
import urllib.request
import pytest

from providers.gate import (
    APPROVED_DOMAINS,
    BLOCKED_DOMAINS,
    FreeFirstPolicyViolationError,
    install_egress_interceptor,
    is_free_only_mode,
    uninstall_egress_interceptor,
    validate_egress_url,
    validate_provider_initialization,
)
from providers.llm import GeminiProvider, OllamaProvider, get_llm_provider
from providers.registry import ProviderRegistry
from providers.websearch import TavilyProvider, get_websearch_provider


def test_free_only_mode_default():
    """Confirms free only mode defaults to True."""
    assert is_free_only_mode() is True


def test_validate_provider_initialization():
    """Confirms paid providers are blocked from initializing."""
    # Prohibited paid providers must raise
    for blocked in ["tavily", "gemini", "openai", "anthropic", "keepa", "serpapi", "apify"]:
        with pytest.raises(FreeFirstPolicyViolationError):
            validate_provider_initialization(blocked)

    # Allowed free providers must not raise
    for allowed in ["ollama", "amzn-sp-api", "gdelt", "csv", "demo", "rules_engine"]:
        validate_provider_initialization(allowed)


def test_gemini_provider_blocked_in_free_only():
    """Attempting to instantiate GeminiProvider must raise in free-only mode."""
    with pytest.raises(FreeFirstPolicyViolationError):
        GeminiProvider()


def test_tavily_provider_blocked_in_free_only():
    """Attempting to instantiate TavilyProvider must raise in free-only mode."""
    with pytest.raises(FreeFirstPolicyViolationError):
        TavilyProvider()


def test_get_llm_provider_gemini_blocked():
    """Configuring LLM_PROVIDER=gemini raises error in free-only mode."""
    old_val = os.environ.get("LLM_PROVIDER")
    try:
        os.environ["LLM_PROVIDER"] = "gemini"
        with pytest.raises(FreeFirstPolicyViolationError):
            get_llm_provider()
    finally:
        if old_val:
            os.environ["LLM_PROVIDER"] = old_val
        else:
            os.environ.pop("LLM_PROVIDER", None)


def test_ollama_provider_allowed():
    """OllamaProvider initializes cleanly without error."""
    provider = OllamaProvider()
    assert provider.name == "ollama"
    assert provider.is_configured() is True


def test_validate_egress_url():
    """Verifies approved and blocked domain egress validation."""
    # Approved domains
    for domain in APPROVED_DOMAINS:
        validate_egress_url(f"https://{domain}/api/v1/test")

    # Explicitly blocked domains
    for domain in BLOCKED_DOMAINS:
        with pytest.raises(FreeFirstPolicyViolationError):
            validate_egress_url(f"https://{domain}/v1/search")

    # Unapproved arbitrary domain
    with pytest.raises(FreeFirstPolicyViolationError):
        validate_egress_url("https://unapproved-third-party-api.com/data")


def test_egress_interceptor_blocks_urllib():
    """Verifies urlopen interceptor raises FreeFirstPolicyViolationError on prohibited outbound call."""
    install_egress_interceptor()
    try:
        with pytest.raises(FreeFirstPolicyViolationError):
            urllib.request.urlopen("https://api.tavily.com/search")
    finally:
        uninstall_egress_interceptor()


def test_egress_interceptor_blocks_socket_and_http_client():
    """Verifies socket interceptor blocks low-level sockets and http.client."""
    import http.client

    install_egress_interceptor()
    try:
        with pytest.raises(FreeFirstPolicyViolationError):
            conn = http.client.HTTPConnection("api.tavily.com", timeout=1)
            conn.request("GET", "/")
    finally:
        uninstall_egress_interceptor()


def test_api_health_reports_free_only_mode():
    """Verifies that GET /api/health exposes free_only_mode accurately."""
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "free_only_mode" in data
    assert data["free_only_mode"] is True


def test_research_api_blocks_live_calls_in_free_only():
    """Verifies that POST /api/research rejects live un-cached calls when FREE_ONLY=true."""
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    resp = client.post("/api/research", json={"product_name": "Test Product New", "use_cache": False})
    assert resp.status_code == 403
    assert "FREE_ONLY" in resp.json()["detail"]


def test_provider_registry_gate():
    """Verifies ProviderRegistry refuses paid providers."""
    registry = ProviderRegistry()

    # Can register allowed provider
    registry.register("ollama", OllamaProvider())
    assert registry.has("ollama")

    # Cannot register paid provider
    class DummyPaidProvider:
        name = "tavily"

    with pytest.raises(FreeFirstPolicyViolationError):
        registry.register("tavily", DummyPaidProvider(), is_paid=True)
