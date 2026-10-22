"""
llm.py — pluggable LLM provider for the four intelligence modules.
Deterministic analysis (see intelligence/) never depends on any of this;
these providers only produce the OPTIONAL plain-English explanation layer
on top of already-verified, already-calculated data.

Real implementations: Ollama, Gemini, plus free-tier OpenAI-compatible
Groq/OpenRouter and an `auto` fallback chain (see the classes below).
The first two:
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
from urllib.error import HTTPError, URLError

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


class OpenAICompatProvider:
    """Any OpenAI-compatible `/chat/completions` endpoint with a free tier.
    Two presets are wired up below (Groq, OpenRouter); both need only a
    free API key, never a payment method on the code side.

    Uses JSON-object mode plus the pydantic JSON schema spelled out in the
    system prompt, then validates the reply with pydantic -- same
    "model proposes, schema disposes" rule as the other providers. A reply
    that is not valid JSON for the schema becomes `available=False`, never
    a guess. Plain urllib on purpose: no new dependency.

    NOT verified against the live services in the build environment (its
    shell cannot reach them) -- the request/response handling is covered
    by mocked-HTTP tests only. Run one real call before relying on it."""

    def __init__(self, name: str, base_url: str, api_key_env: str, model_env: str, default_model: str | None) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.model = os.environ.get(model_env) or default_model or ""

    def is_configured(self) -> bool:
        return bool(os.environ.get(self.api_key_env)) and bool(self.model)

    def explain(self, system: str, prompt: str, schema: type[T]) -> LLMResult:
        if not os.environ.get(self.api_key_env):
            return LLMResult(False, None, self.name, self.model, f"{self.api_key_env} not configured")
        if not self.model:
            return LLMResult(False, None, self.name, self.model, f"No model set for {self.name}; set its *_MODEL variable")
        schema_text = json.dumps(schema.model_json_schema())
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"{system}\n\nRespond with ONLY a JSON object that matches this JSON schema:\n{schema_text}"},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 2048,
        }
        req = urllib_request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ[self.api_key_env]}",
                # Some CDNs in front of these APIs reject urllib's default agent.
                "User-Agent": "commercesense-ai/1.0",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
        except HTTPError as exc:
            return LLMResult(False, None, self.name, self.model, f"{self.name} HTTP {exc.code}")
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            return LLMResult(False, None, self.name, self.model, f"{self.name} unreachable: {exc}")

        try:
            raw = result["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            return LLMResult(False, None, self.name, self.model, f"Unexpected {self.name} response shape")
        raw = raw.strip()
        if raw.startswith("```"):  # some models fence the JSON despite json_object mode
            raw = raw.strip("`").removeprefix("json").strip()
        if not raw:
            return LLMResult(False, None, self.name, self.model, f"Empty response from {self.name}")
        try:
            data = schema.model_validate(json.loads(raw))
        except Exception as exc:  # noqa: BLE001
            return LLMResult(False, None, self.name, self.model, f"Could not parse {self.name} output as {schema.__name__}: {exc}")
        return LLMResult(True, data, self.name, self.model)


def GroqProvider() -> OpenAICompatProvider:  # noqa: N802 -- reads like the other provider classes
    """Groq's OpenAI-compatible API. Model IDs and free-plan limits change;
    Groq's rate-limits page listed `openai/gpt-oss-20b` (30 req/min,
    1,000 req/day on the free plan) when this was added. Override with GROQ_MODEL."""
    return OpenAICompatProvider("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL", "openai/gpt-oss-20b")


def OpenRouterProvider() -> OpenAICompatProvider:  # noqa: N802
    """OpenRouter. There is deliberately NO default model: which models are
    free changes often, so OPENROUTER_MODEL must be set explicitly (pick one
    whose ID ends in `:free` from openrouter.ai/models)."""
    return OpenAICompatProvider("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", None)


class ChainProvider:
    """LLM_PROVIDER=auto. Tries each configured provider in LLM_CHAIN order
    (default gemini,groq,openrouter,ollama) and returns the first one that
    produces a valid result, so a free tier hitting its rate limit falls
    through to the next instead of losing the explanation. The result's
    `provider`/`model` name whichever provider actually answered. If every
    provider fails, the error lists each failure; nothing is fabricated."""

    name = "auto"

    def __init__(self, providers: list[LLMProvider] | None = None) -> None:
        self.providers = providers if providers is not None else _build_chain()

    def is_configured(self) -> bool:
        return any(p.is_configured() for p in self.providers)

    def explain(self, system: str, prompt: str, schema: type[T]) -> LLMResult:
        errors: list[str] = []
        for provider in self.providers:
            if not provider.is_configured():
                continue
            result = provider.explain(system, prompt, schema)
            if result.available:
                return result
            errors.append(f"{result.provider}: {result.error}")
        if not errors:
            return LLMResult(False, None, self.name, "-", "No LLM provider is configured")
        return LLMResult(False, None, self.name, "-", "; ".join(errors))


_PROVIDER_FACTORIES = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
    "ollama": OllamaProvider,
}


def _build_chain() -> list[LLMProvider]:
    order = os.environ.get("LLM_CHAIN", "gemini,groq,openrouter,ollama")
    names = [n.strip().lower() for n in order.split(",") if n.strip()]
    return [_PROVIDER_FACTORIES[n]() for n in names if n in _PROVIDER_FACTORIES]


def get_llm_provider() -> LLMProvider:
    choice = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if choice == "auto":
        return ChainProvider()
    factory = _PROVIDER_FACTORIES.get(choice)
    return factory() if factory else OllamaProvider()
