"""
llm.py — pluggable LLM provider for the four intelligence modules.
Deterministic analysis (see intelligence/) never depends on any of this;
these providers only produce the OPTIONAL plain-English explanation layer
on top of already-verified, already-calculated data.

Two real implementations:
  - OllamaProvider (default): local, free, verified working against a real
    running Ollama instance during development of this module (see commit
    history / CLAUDE.md). Uses /api/generate with a JSON-schema `format`
    constraint, the same "schema-constrained output" idea already used for
    Gemini in agent/insight_agent.py. One real, verified quirk of this
    Ollama build + the qwen3-vl model family: structured JSON output lands
    in the `thinking` field instead of `response`, even with think=False.
    Handled by trying `response` first and falling back to `thinking`.
  - GeminiProvider: reuses the exact call pattern already proven in
    agent/insight_agent.py (structured output, AFC explicitly disabled).

If neither is reachable/configured, callers get back
LLMResult(available=False, ...) and must degrade gracefully — never crash,
never fabricate an explanation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol, TypeVar
from urllib import request as urllib_request
from urllib.error import URLError

from pydantic import BaseModel

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

    def explain(self, system: str, prompt: str, schema: type[T]) -> LLMResult: ...


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        self.model = os.environ.get("INTELLIGENCE_GEMINI_MODEL", "gemini-3.6-flash")

    def is_configured(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))

    def explain(self, system: str, prompt: str, schema: type[T]) -> LLMResult:
        if not self.is_configured():
            return LLMResult(False, None, self.name, self.model, "GEMINI_API_KEY not configured")
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(
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
            parsed = response.parsed
            if parsed is None:
                return LLMResult(False, None, self.name, self.model, "No parsed output (possibly truncated)")
            data = parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
            return LLMResult(True, data, self.name, self.model)
        except Exception as exc:  # noqa: BLE001 — provider must never raise into a caller
            return LLMResult(False, None, self.name, self.model, str(exc))


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "qwen3-vl:4b")

    def is_configured(self) -> bool:
        # Always "configured" in the sense of having a target URL; actual
        # reachability is only known at call time, same as any HTTP call.
        return True

    def explain(self, system: str, prompt: str, schema: type[T]) -> LLMResult:
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
            with urllib_request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
        except (URLError, TimeoutError, OSError) as exc:
            return LLMResult(False, None, self.name, self.model, f"Ollama unreachable at {self.base_url}: {exc}")

        # Verified quirk: some model families put schema-constrained output
        # in `thinking` instead of `response` even with think disabled.
        raw = result.get("response") or result.get("thinking") or ""
        if not raw.strip():
            return LLMResult(False, None, self.name, self.model, "Empty response from Ollama")
        try:
            data = schema.model_validate(json.loads(raw))
        except Exception as exc:  # noqa: BLE001
            return LLMResult(False, None, self.name, self.model, f"Could not parse Ollama output as {schema.__name__}: {exc}")
        return LLMResult(True, data, self.name, self.model)


def get_llm_provider() -> LLMProvider:
    choice = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if choice == "gemini":
        return GeminiProvider()
    return OllamaProvider()
