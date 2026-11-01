"""
llm.py — pluggable LLM provider for the intelligence modules and agent layer.
Deterministic analysis never depends on any of this; these providers only produce
the plain-English explanation layer on top of verified, calculated data.

Implementations:
  - OllamaProvider (default): local, free, zero API key required.
    Hardened for CommerceSense AI v3:
      * Timeout configurable via OLLAMA_TIMEOUT_SECONDS (default 15.0s)
      * Quirk mitigation for qwen3-vl / deepseek structured outputs in `thinking` field
      * Strips markdown fences (```json ... ```) automatically
      * Strict fallback returning LLMResult(available=False, ...) with deterministic outputs
      * Health check diagnostic method
  - GeminiProvider: hosted proprietary LLM.
    Strictly BLOCKED under FREE_ONLY=true hard gate policy.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Protocol, TypeVar
from urllib import request as urllib_request
from urllib.error import URLError

from pydantic import BaseModel

from providers.gate import (
    FreeFirstPolicyViolationError,
    is_free_only_mode,
    validate_egress_url,
    validate_provider_initialization,
)

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMResult:
    available: bool
    data: BaseModel | None
    provider: str
    model: str
    error: str | None = None


class LLMProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def explain(self, system: str, prompt: str, schema: type[T], fallback_data: T | None = None) -> LLMResult: ...

    def health_check(self) -> Dict[str, Any]: ...


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        validate_provider_initialization(self.name)
        self.model = os.environ.get("INTELLIGENCE_GEMINI_MODEL", "gemini-3.6-flash")

    def is_configured(self) -> bool:
        if is_free_only_mode():
            return False
        return bool(os.environ.get("GEMINI_API_KEY"))

    def explain(self, system: str, prompt: str, schema: type[T], fallback_data: T | None = None) -> LLMResult:
        if is_free_only_mode():
            raise FreeFirstPolicyViolationError("GeminiProvider is blocked under FREE_ONLY=true policy")
        if not self.is_configured():
            return LLMResult(False, fallback_data, self.name, self.model, "GEMINI_API_KEY not configured")
        try:
            from google.genai import types
            from providers.gemini_rotator import gemini_rotator

            def _call(client):
                return client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=schema,
                        max_output_tokens=1024,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )

            response = gemini_rotator.execute_with_rotation(_call)
            parsed = response.parsed
            if parsed is None:
                return LLMResult(False, None, self.name, self.model, "No parsed output (possibly truncated)")
            data = parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
            return LLMResult(True, data, self.name, self.model)
        except Exception as exc:  # noqa: BLE001 — provider must never raise into a caller
            return LLMResult(False, None, self.name, self.model, str(exc))

    def health_check(self) -> Dict[str, Any]:
        if is_free_only_mode():
            return {"status": "blocked", "provider": self.name, "reason": "FREE_ONLY policy active"}
        return {"status": "ok" if self.is_configured() else "unconfigured", "provider": self.name}


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "qwen3-vl:4b")
        timeout_env = os.environ.get("OLLAMA_TIMEOUT_SECONDS", "15.0")
        try:
            self.timeout = float(timeout_env)
        except (ValueError, TypeError):
            self.timeout = 15.0
        # Validate that base_url is an approved local host
        validate_egress_url(self.base_url)

    def is_configured(self) -> bool:
        return True

    def health_check(self) -> Dict[str, Any]:
        """Pings local Ollama service to check connectivity and list models."""
        try:
            req = urllib_request.Request(
                f"{self.base_url}/api/tags",
                headers={"Accept": "application/json"},
            )
            with urllib_request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            return {
                "status": "online",
                "base_url": self.base_url,
                "configured_model": self.model,
                "available_models": models,
                "model_present": any(self.model in m for m in models),
            }
        except Exception as exc:
            return {
                "status": "offline",
                "base_url": self.base_url,
                "configured_model": self.model,
                "error": str(exc),
            }

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Strips ```json ... ``` or ``` ... ``` markdown fences from LLM output."""
        cleaned = text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence_match:
            return fence_match.group(1).strip()
        return cleaned

    def explain(
        self,
        system: str,
        prompt: str,
        schema: type[T],
        fallback_data: T | None = None,
    ) -> LLMResult:
        full_prompt = f"{system}\n\n{prompt}"
        body = {
            "model": self.model,
            "prompt": full_prompt,
            "format": schema.model_json_schema(),
            "stream": False,
            "think": False,
            "options": {"num_predict": 600},
        }
        try:
            req = urllib_request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib_request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError) as exc:
            return LLMResult(
                False, fallback_data, self.name, self.model,
                f"Ollama unreachable at {self.base_url}: {exc}"
            )
        except Exception as exc:
            return LLMResult(
                False, fallback_data, self.name, self.model,
                f"Unexpected error communicating with Ollama: {exc}"
            )

        # Quirk mitigation: check response first, then thinking field
        raw = result.get("response") or result.get("thinking") or ""
        if not raw.strip():
            return LLMResult(False, fallback_data, self.name, self.model, "Empty response from Ollama")

        cleaned_json = self._strip_markdown_fences(raw)

        parsed_dict = None
        try:
            parsed_dict = json.loads(cleaned_json)
        except Exception:
            start = cleaned_json.find("{")
            end = cleaned_json.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed_dict = json.loads(cleaned_json[start : end + 1])
                except Exception:
                    pass

        if parsed_dict is not None:
            try:
                data = schema.model_validate(parsed_dict)
                return LLMResult(True, data, self.name, self.model)
            except Exception as exc:  # noqa: BLE001
                return LLMResult(
                    False, fallback_data, self.name, self.model,
                    f"Could not parse Ollama output as {schema.__name__}: {exc}"
                )

        return LLMResult(
            False, fallback_data, self.name, self.model,
            f"Could not parse Ollama output as {schema.__name__}: invalid JSON format"
        )


def get_llm_provider() -> LLMProvider:
    choice = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if choice == "gemini":
        if is_free_only_mode():
            raise FreeFirstPolicyViolationError(
                "GeminiProvider cannot be used when FREE_ONLY=true. Use OllamaProvider or set ALLOW_PAID_PROVIDERS=true."
            )
        return GeminiProvider()
    return OllamaProvider()
