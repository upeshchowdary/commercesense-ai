"""
registry.py — Central Provider Registry with strict Free-First Hard Gate.

Coordinates LLM, WebSearch, and Amazon data providers, ensuring no paid APIs
can initialize when FREE_ONLY=true.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Type

from providers.gate import (
    FreeFirstPolicyViolationError,
    is_free_only_mode,
    validate_provider_initialization,
)
from providers.provenance import (
    DATA_SOURCE_REGISTRY,
    ProvenanceEnvelope,
    SourceCapability,
    is_provider_allowed,
)


class ProviderRegistry:
    """Registry managing provider instances and lifecycle under Free-First constraints."""

    _instance: Optional["ProviderRegistry"] = None
    _providers: Dict[str, Any] = {}

    def __init__(self) -> None:
        self._providers = {}

    @classmethod
    def get_instance(cls) -> "ProviderRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name: str, provider_instance: Any, is_paid: bool = False) -> None:
        """Registers a provider instance, enforcing the Free-First hard gate."""
        if is_free_only_mode() and is_paid:
            raise FreeFirstPolicyViolationError(
                f"Cannot register paid provider '{name}' when FREE_ONLY=true"
            )
        validate_provider_initialization(name)
        self._providers[name.lower()] = provider_instance

    def get(self, name: str) -> Any:
        """Retrieves a registered provider instance."""
        validate_provider_initialization(name)
        return self._providers.get(name.lower())

    def has(self, name: str) -> bool:
        return name.lower() in self._providers

    def clear(self) -> None:
        self._providers.clear()


def get_active_provider_registry() -> ProviderRegistry:
    return ProviderRegistry.get_instance()
