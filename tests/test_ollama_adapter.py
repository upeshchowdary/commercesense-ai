"""
test_ollama_adapter.py — Tests for local Ollama adapter, quirk mitigation, and deterministic fallback.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError
import pytest
from pydantic import BaseModel

from providers.llm import OllamaProvider


class SampleExplanationSchema(BaseModel):
    summary: str
    key_factors: list[str]
    confidence_score: float


def test_ollama_provider_initialization():
    """Verifies Ollama provider configures base URL and default model."""
    provider = OllamaProvider()
    assert provider.name == "ollama"
    assert provider.base_url.startswith("http://")
    assert provider.timeout > 0


def test_ollama_strip_markdown_fences():
    """Verifies that markdown json fences are cleanly stripped."""
    raw1 = "```json\n{\"summary\": \"test\", \"key_factors\": [], \"confidence_score\": 0.9}\n```"
    stripped1 = OllamaProvider._strip_markdown_fences(raw1)
    parsed1 = json.loads(stripped1)
    assert parsed1["summary"] == "test"

    raw2 = "```\n{\"summary\": \"raw\", \"key_factors\": [\"f1\"], \"confidence_score\": 0.8}\n```"
    stripped2 = OllamaProvider._strip_markdown_fences(raw2)
    parsed2 = json.loads(stripped2)
    assert parsed2["summary"] == "raw"


def test_ollama_offline_fallback():
    """When Ollama is unreachable, returns LLMResult(available=False) without crashing."""
    provider = OllamaProvider()

    with patch("urllib.request.urlopen", side_effect=URLError("Connection refused")):
        res = provider.explain("system", "prompt", SampleExplanationSchema)

    assert res.available is False
    assert res.data is None
    assert "unreachable" in (res.error or "").lower()


def test_ollama_qwen_quirk_thinking_field():
    """When Ollama output lands in 'thinking' instead of 'response', parses correctly."""
    provider = OllamaProvider()
    valid_json = json.dumps({
        "summary": "Recovered from thinking field",
        "key_factors": ["factor 1", "factor 2"],
        "confidence_score": 0.95,
    })

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"thinking": valid_json, "response": ""}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = provider.explain("system", "prompt", SampleExplanationSchema)

    assert res.available is True
    assert res.data is not None
    assert res.data.summary == "Recovered from thinking field"
    assert len(res.data.key_factors) == 2


def test_ollama_schema_validation_failure():
    """When Ollama returns invalid JSON, fails gracefully to available=False."""
    provider = OllamaProvider()

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"response": "not valid json"}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = provider.explain("system", "prompt", SampleExplanationSchema)

    assert res.available is False
    assert res.data is None
    assert "could not parse" in (res.error or "").lower()


def test_ollama_commentary_json_extraction():
    """When Ollama emits commentary without markdown fences, extracts JSON between braces."""
    provider = OllamaProvider()
    conversational = (
        'Here is the diagnosis you asked for: '
        '{"summary": "Extracted despite commentary", "key_factors": ["bullet 1"], "confidence_score": 0.88} '
        'Hope that helps!'
    )
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"response": conversational}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = provider.explain("system", "prompt", SampleExplanationSchema)

    assert res.available is True
    assert res.data is not None
    assert res.data.summary == "Extracted despite commentary"
    assert res.data.confidence_score == 0.88


def test_ollama_offline_returns_fallback_data():
    """When Ollama is offline, returns fallback_data with available=False."""
    provider = OllamaProvider()
    fallback = SampleExplanationSchema(summary="Fallback rule result", key_factors=["f0"], confidence_score=0.5)

    with patch("urllib.request.urlopen", side_effect=URLError("Connection refused")):
        res = provider.explain("system", "prompt", SampleExplanationSchema, fallback_data=fallback)

    assert res.available is False
    assert res.data == fallback
    assert res.data.summary == "Fallback rule result"


def test_ollama_health_check_offline():
    """Health check reports offline status when daemon is not running."""
    provider = OllamaProvider()

    with patch("urllib.request.urlopen", side_effect=URLError("Connection refused")):
        status = provider.health_check()

    assert status["status"] == "offline"
    assert "error" in status
