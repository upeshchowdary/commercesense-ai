"""
gate.py — Strict Free-First Policy Hard Gate & Egress Interceptor for CommerceSense AI v3.

Enforces:
  1. FREE_ONLY=true & ALLOW_PAID_PROVIDERS=false hard policy.
  2. Provider initialization blocker rejecting paid APIs (Tavily, Gemini, OpenAI, Keepa, SerpAPI).
  3. Outbound network interceptor blocking HTTP traffic to unapproved domains.
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse
from typing import Set


class FreeFirstPolicyViolationError(RuntimeError):
    """Raised when an operation violates the strict Free-First architecture policy."""
    pass


# Domains explicitly permitted for external network calls in FREE_ONLY mode
APPROVED_DOMAINS: Set[str] = {
    # Official Amazon SP-API and LWA endpoints
    "sellingpartnerapi-eu.amazon.com",
    "sellingpartnerapi-na.amazon.com",
    "sellingpartnerapi-fe.amazon.com",
    "sandbox.sellingpartnerapi-na.amazon.com",
    "api.amazon.com",
    "amazonaws.com",
    "media-amazon.com",
    # Free Public News, Trends & RSS Endpoints
    "api.gdeltproject.org",
    "news.google.com",
    "cpsc.gov",
    "www.cpsc.gov",
    "feeds.feedburner.com",
    "trends.google.com",
    # Free Search & Encyclopedic Data
    "duckduckgo.com",
    "html.duckduckgo.com",
    "api.duckduckgo.com",
    "en.wikipedia.org",
    "wikipedia.org",
    # Google AI Studio Free Tier (Rotating Pool of 9 keys)
    "generativelanguage.googleapis.com",
    # Local Services (Ollama, PostgreSQL, Valkey, Test Server)
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "testserver",
}

# Domains explicitly prohibited and blocked
BLOCKED_DOMAINS: Set[str] = {
    "api.tavily.com",
    "tavily.com",
    "api.keepa.com",
    "keepa.com",
    "api.serpapi.com",
    "serpapi.com",
    "api.apify.com",
    "apify.com",
    "api.openai.com",
    "openai.com",
    "api.anthropic.com",
    "anthropic.com",
}

# Provider names prohibited when FREE_ONLY=true
PAID_PROVIDERS: Set[str] = {
    "tavily",
    "gemini",
    "openai",
    "anthropic",
    "keepa",
    "serpapi",
    "apify",
}


def is_free_only_mode() -> bool:
    """Returns True if the system is running under the FREE_ONLY constraint."""
    free_only_val = os.environ.get("FREE_ONLY", "true").strip().lower()
    allow_paid_val = os.environ.get("ALLOW_PAID_PROVIDERS", "false").strip().lower()
    free_only = free_only_val in ("true", "1", "yes")
    allow_paid = allow_paid_val in ("true", "1", "yes")
    if allow_paid:
        return False
    return free_only


def validate_provider_initialization(provider_name: str) -> None:
    """Blocks initialization of paid providers when FREE_ONLY=true."""
    norm_name = provider_name.strip().lower()
    if is_free_only_mode() and norm_name in PAID_PROVIDERS:
        raise FreeFirstPolicyViolationError(
            f"Provider '{provider_name}' is blocked under strict FREE_ONLY policy. "
            f"Paid external APIs are strictly prohibited in CommerceSense AI v3."
        )


def validate_egress_url(url_or_host: str) -> None:
    """Checks whether an outbound network destination is allowed under FREE_ONLY policy."""
    if not is_free_only_mode():
        return

    if not url_or_host:
        return

    # Extract hostname
    if "://" in url_or_host:
        parsed = urlparse(url_or_host)
        host = (parsed.hostname or "").lower()
    else:
        # Check if it has a port (e.g. host:port or [::1]:port)
        clean = url_or_host.strip()
        if clean.startswith("[") and "]" in clean:
            host = clean[1:clean.index("]")].lower()
        elif ":" in clean:
            host = clean.split(":")[0].lower()
        else:
            host = clean.lower()

    if not host:
        return

    # Direct match on blocked list
    for blocked in BLOCKED_DOMAINS:
        if host == blocked or host.endswith("." + blocked):
            raise FreeFirstPolicyViolationError(
                f"Egress to prohibited domain '{host}' blocked by FREE_ONLY hard gate."
            )

    # Allow approved domains and their subdomains
    is_approved = False
    for approved in APPROVED_DOMAINS:
        if host == approved or host.endswith("." + approved):
            is_approved = True
            break

    if not is_approved:
        raise FreeFirstPolicyViolationError(
            f"Outbound network call to '{host}' blocked. Host is not in the approved domain allowlist: {sorted(APPROVED_DOMAINS)}"
        )


_ORIGINAL_URLOPEN = None
_ORIGINAL_CREATE_CONNECTION = None
_INTERCEPTOR_INSTALLED = False


def install_egress_interceptor() -> None:
    """Installs monkey-patches on standard library HTTP and socket clients to enforce the egress filter."""
    global _ORIGINAL_URLOPEN, _ORIGINAL_CREATE_CONNECTION, _INTERCEPTOR_INSTALLED
    if _INTERCEPTOR_INSTALLED:
        return

    import socket
    import urllib.request

    _ORIGINAL_URLOPEN = urllib.request.urlopen
    _ORIGINAL_CREATE_CONNECTION = socket.create_connection

    def gated_urlopen(url_or_req, *args, **kwargs):
        if hasattr(url_or_req, "full_url"):
            target_url = url_or_req.full_url
        elif isinstance(url_or_req, str):
            target_url = url_or_req
        else:
            target_url = str(url_or_req)

        validate_egress_url(target_url)
        return _ORIGINAL_URLOPEN(url_or_req, *args, **kwargs)

    def gated_create_connection(address, *args, **kwargs):
        if isinstance(address, tuple) and len(address) >= 1:
            validate_egress_url(str(address[0]))
        elif isinstance(address, str):
            validate_egress_url(address)
        return _ORIGINAL_CREATE_CONNECTION(address, *args, **kwargs)

    urllib.request.urlopen = gated_urlopen
    socket.create_connection = gated_create_connection
    _INTERCEPTOR_INSTALLED = True


def uninstall_egress_interceptor() -> None:
    """Restores the original urlopen and socket.create_connection functions."""
    global _ORIGINAL_URLOPEN, _ORIGINAL_CREATE_CONNECTION, _INTERCEPTOR_INSTALLED
    if not _INTERCEPTOR_INSTALLED:
        return

    import socket
    import urllib.request

    if _ORIGINAL_URLOPEN is not None:
        urllib.request.urlopen = _ORIGINAL_URLOPEN
        _ORIGINAL_URLOPEN = None
    if _ORIGINAL_CREATE_CONNECTION is not None:
        socket.create_connection = _ORIGINAL_CREATE_CONNECTION
        _ORIGINAL_CREATE_CONNECTION = None
    _INTERCEPTOR_INSTALLED = False
