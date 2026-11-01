"""
gemini_rotator.py — Gemini API Key rotation and automatic rate-limit/quota fallback.

Manages a pool of Gemini API keys. When one key hits rate limits (429), quota
exhaustion (RESOURCE_EXHAUSTED), or API errors, it automatically switches to
the next key in the pool and retries the operation seamlessly.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Callable, List, TypeVar

logger = logging.getLogger("gemini_rotator")

T = TypeVar("T")

DEFAULT_KEYS: List[str] = [
    k.strip()
    for k in os.environ.get("GEMINI_API_KEYS", os.environ.get("GEMINI_API_KEY", "")).split(",")
    if k.strip()
]


class GeminiKeyRotator:
    """Thread-safe key rotator for Google Gemini API."""

    def __init__(self, keys: list[str] | None = None) -> None:
        self._lock = threading.Lock()
        self._keys: list[str] = []
        self._index: int = 0
        self.reload_keys(keys)

    def reload_keys(self, explicit_keys: list[str] | None = None) -> None:
        """Loads keys from explicit list, GEMINI_API_KEYS env var, or DEFAULT_KEYS."""
        with self._lock:
            if explicit_keys:
                self._keys = [k.strip() for k in explicit_keys if k.strip()]
            else:
                env_keys = os.environ.get("GEMINI_API_KEYS", "")
                if env_keys:
                    # Parse comma or newline separated
                    raw = [k.strip() for k in env_keys.replace("\n", ",").split(",") if k.strip()]
                    self._keys = raw if raw else list(DEFAULT_KEYS)
                else:
                    single_key = os.environ.get("GEMINI_API_KEY", "").strip()
                    if single_key and single_key not in DEFAULT_KEYS:
                        self._keys = [single_key] + [k for k in DEFAULT_KEYS if k != single_key]
                    else:
                        self._keys = list(DEFAULT_KEYS)

            self._index = 0
            if self._keys:
                os.environ["GEMINI_API_KEY"] = self._keys[0]

    @property
    def total_keys(self) -> int:
        with self._lock:
            return len(self._keys)

    def get_current_key(self) -> str:
        with self._lock:
            if not self._keys:
                raise ValueError("No Gemini API keys configured.")
            return self._keys[self._index]

    def _mask_key(self, key: str) -> str:
        if len(key) <= 12:
            return "***"
        return f"{key[:8]}...{key[-4:]}"

    def rotate_to_next(self, reason: str = "") -> str:
        """Rotates to the next key in the pool and updates GEMINI_API_KEY in os.environ."""
        with self._lock:
            if not self._keys:
                raise ValueError("No Gemini API keys configured.")
            old_key = self._keys[self._index]
            self._index = (self._index + 1) % len(self._keys)
            new_key = self._keys[self._index]
            os.environ["GEMINI_API_KEY"] = new_key
            logger.warning(
                "Rotated Gemini API Key: [%s] -> [%s] (key %d/%d). Reason: %s",
                self._mask_key(old_key),
                self._mask_key(new_key),
                self._index + 1,
                len(self._keys),
                reason or "manual/quota",
            )
            return new_key

    def get_client(self):
        """Returns a google.genai.Client configured with the current active key."""
        from google import genai

        return genai.Client(api_key=self.get_current_key())

    def is_quota_or_rate_limit_error(self, exc: Exception) -> bool:
        """Checks if an exception is caused by 429, quota exhaustion, or rate limit."""
        err_str = str(exc).lower()
        err_type = type(exc).__name__.lower()

        quota_signatures = [
            "429",
            "resource_exhausted",
            "quota",
            "rate_limit",
            "rate limit",
            "too many requests",
            "exhausted",
            "limit exceeded",
        ]

        if any(sig in err_str for sig in quota_signatures):
            return True
        if any(sig in err_type for sig in quota_signatures):
            return True

        # Check status_code or code attributes if present on APIError
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if code in (429, "RESOURCE_EXHAUSTED"):
            return True

        return False

    def execute_with_rotation(self, func: Callable[[any], T], max_attempts: int | None = None) -> T:
        """
        Executes func(client) using the active Gemini client.
        If a quota or rate-limit error occurs, rotates to the next key and retries.
        """
        attempts = 0
        total = self.total_keys
        limit = max_attempts if max_attempts is not None else total

        last_error: Exception | None = None

        while attempts < limit:
            attempts += 1
            client = self.get_client()
            try:
                return func(client)
            except Exception as exc:
                last_error = exc
                if self.is_quota_or_rate_limit_error(exc):
                    logger.warning(
                        "Gemini call failed with quota/rate limit error (attempt %d/%d): %s",
                        attempts,
                        limit,
                        exc,
                    )
                    self.rotate_to_next(reason=str(exc)[:100])
                    continue
                else:
                    # Non-quota error, raise directly unless it's an auth error on a specific key
                    if "api_key" in str(exc).lower() or "invalid api key" in str(exc).lower():
                        logger.warning("Gemini call failed with auth error on key, rotating: %s", exc)
                        self.rotate_to_next(reason="invalid_key")
                        continue
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("All Gemini API keys in rotation pool exhausted.")


# Global singleton instance
gemini_rotator = GeminiKeyRotator()

