"""Tests for the free-tier integrations: OpenAI-compatible LLM providers
(Groq/OpenRouter), the `auto` fallback chain, the keyless search fallback and
the CPSC recall check.

None of these touch the network: HTTP is replaced with canned responses, so
they prove the request/response handling and the grounding rules, NOT that the
live services behave the same way. Live behaviour is a manual check."""

import io
import json
from urllib.error import HTTPError, URLError

import pytest
from pydantic import BaseModel

import keyless_search
from providers import llm, recalls


class _Reply(BaseModel):
    summary: str
    confidence: str


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _chat_response(content: str) -> _FakeResponse:
    return _FakeResponse(json.dumps({"choices": [{"message": {"content": content}}]}).encode())


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("GROQ_API_KEY", "GROQ_MODEL", "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
                "GEMINI_API_KEY", "LLM_PROVIDER", "LLM_CHAIN", "ENABLE_KEYLESS_SEARCH"):
        monkeypatch.delenv(var, raising=False)
    recalls._cache.clear()


# ---------------------------------------------------------------- OpenAI-compatible providers

def test_groq_returns_validated_data_and_sends_bearer_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = json.loads(req.data)
        return _chat_response('{"summary": "ok", "confidence": "high"}')

    monkeypatch.setattr(llm.urllib_request, "urlopen", fake_urlopen)
    result = llm.GroqProvider().explain("sys", "prompt", _Reply)

    assert result.available and result.provider == "groq"
    assert result.data == _Reply(summary="ok", confidence="high")
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert "summary" in seen["body"]["messages"][0]["content"]  # schema is in the system prompt


def test_markdown_fenced_json_is_accepted(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(llm.urllib_request, "urlopen",
                        lambda req, timeout=0: _chat_response('```json\n{"summary": "x", "confidence": "low"}\n```'))
    assert llm.GroqProvider().explain("s", "p", _Reply).available


def test_output_that_violates_the_schema_is_rejected_not_guessed(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(llm.urllib_request, "urlopen", lambda req, timeout=0: _chat_response('{"summary": "only one field"}'))
    result = llm.GroqProvider().explain("s", "p", _Reply)
    assert not result.available and result.data is None and "Could not parse" in result.error


def test_http_error_and_network_error_degrade_without_raising(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")

    def rate_limited(req, timeout=0):
        raise HTTPError(req.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(llm.urllib_request, "urlopen", rate_limited)
    result = llm.GroqProvider().explain("s", "p", _Reply)
    assert not result.available and "429" in result.error

    def offline(req, timeout=0):
        raise URLError("no route")

    monkeypatch.setattr(llm.urllib_request, "urlopen", offline)
    assert not llm.GroqProvider().explain("s", "p", _Reply).available


def test_missing_key_and_openrouter_without_model_are_unconfigured(monkeypatch):
    assert not llm.GroqProvider().is_configured()
    assert "GROQ_API_KEY" in llm.GroqProvider().explain("s", "p", _Reply).error

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    assert not llm.OpenRouterProvider().is_configured()  # no default model on purpose
    monkeypatch.setenv("OPENROUTER_MODEL", "vendor/some-model:free")
    assert llm.OpenRouterProvider().is_configured()


# ---------------------------------------------------------------- fallback chain

class _Stub:
    def __init__(self, name, configured, ok):
        self.name, self._configured, self._ok = name, configured, ok
        self.calls = 0

    def is_configured(self):
        return self._configured

    def explain(self, system, prompt, schema):
        self.calls += 1
        if self._ok:
            return llm.LLMResult(True, schema(summary=self.name, confidence="high"), self.name, "m")
        return llm.LLMResult(False, None, self.name, "m", "rate limited")


def test_chain_falls_through_to_the_next_provider_and_reports_who_answered():
    first, second, third = _Stub("gemini", True, False), _Stub("groq", True, True), _Stub("ollama", True, True)
    result = llm.ChainProvider([first, second, third]).explain("s", "p", _Reply)
    assert result.available and result.provider == "groq"
    assert third.calls == 0  # stops at the first success


def test_chain_skips_unconfigured_providers_without_calling_them():
    skipped, used = _Stub("gemini", False, True), _Stub("ollama", True, True)
    llm.ChainProvider([skipped, used]).explain("s", "p", _Reply)
    assert skipped.calls == 0 and used.calls == 1


def test_chain_reports_every_failure_when_all_fail_and_never_fabricates():
    result = llm.ChainProvider([_Stub("gemini", True, False), _Stub("groq", True, False)]).explain("s", "p", _Reply)
    assert not result.available and result.data is None
    assert "gemini: rate limited" in result.error and "groq: rate limited" in result.error
    assert llm.ChainProvider([_Stub("gemini", False, True)]).explain("s", "p", _Reply).error == "No LLM provider is configured"


def test_provider_selection_from_env(monkeypatch):
    assert llm.get_llm_provider().name == "ollama"  # unchanged default
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert llm.get_llm_provider().name == "groq"
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("LLM_CHAIN", "groq, ollama, bogus")
    chain = llm.get_llm_provider()
    assert [p.name for p in chain.providers] == ["groq", "ollama"]
    monkeypatch.setenv("LLM_PROVIDER", "something-unknown")
    assert llm.get_llm_provider().name == "ollama"


# ---------------------------------------------------------------- keyless search fallback

@pytest.fixture
def silent_log(monkeypatch):
    events = []
    monkeypatch.setattr(keyless_search, "log_decision", lambda **kw: events.append(kw))
    return events


def test_keyless_results_are_shaped_like_tavily_results_and_unciteable_ones_dropped(silent_log):
    raw = [
        {"title": "A", "href": "https://example.com/a", "body": "Garlic press costs $14.99 today."},
        {"title": "no url", "href": "", "body": "text without a source"},
        {"title": "no body", "href": "https://example.com/b", "body": ""},
        {"title": "alt keys", "url": "https://example.com/c", "snippet": "Another snippet"},
    ]
    out = keyless_search.keyless_search("q", "P", backend=lambda q, n: raw)
    assert out == [
        {"url": "https://example.com/a", "content": "Garlic press costs $14.99 today."},
        {"url": "https://example.com/c", "content": "Another snippet"},
    ]
    assert silent_log[-1]["action"] == "search_fallback_used"


def test_keyless_failure_and_missing_package_yield_no_findings(silent_log):
    def boom(q, n):
        raise RuntimeError("blocked")

    def missing(q, n):
        raise ImportError("ddgs")

    assert keyless_search.keyless_search("q", "P", backend=boom) == []
    assert keyless_search.keyless_search("q", "P", backend=missing) == []
    assert [e["action"] for e in silent_log] == ["search_failed", "search_backend_missing"]


def test_keyless_search_is_off_unless_explicitly_enabled(monkeypatch):
    assert keyless_search.is_enabled() is False
    monkeypatch.setenv("ENABLE_KEYLESS_SEARCH", "true")
    assert keyless_search.is_enabled() is True


def test_research_agent_uses_fallback_only_when_tavily_gives_nothing(monkeypatch, silent_log):
    import research_agent

    monkeypatch.setattr(research_agent, "log_decision", lambda **kw: None)
    monkeypatch.setattr(research_agent, "_tavily", None)
    monkeypatch.setattr(keyless_search, "is_enabled", lambda: True)
    monkeypatch.setattr(keyless_search, "_default_backend",
                        lambda q, n: [{"href": "https://example.com/x", "body": "from fallback"}])
    assert research_agent._execute_search("q", "P") == [{"url": "https://example.com/x", "content": "from fallback"}]

    class _Tavily:
        def search(self, q, max_results=4):
            return {"results": [{"url": "https://tavily.example/1", "content": "from tavily"}]}

    monkeypatch.setattr(research_agent, "_tavily", _Tavily())
    assert research_agent._execute_search("q", "P")[0]["url"] == "https://tavily.example/1"

    monkeypatch.setattr(keyless_search, "is_enabled", lambda: False)
    monkeypatch.setattr(research_agent, "_tavily", None)
    assert research_agent._execute_search("q", "P") == []  # default behaviour unchanged


# ---------------------------------------------------------------- CPSC recall check

def _record(rid, title, products, date="2025-04-03T00:00:00", manufacturers=None):
    return {
        "RecallID": rid, "RecallNumber": str(rid), "RecallDate": date, "Title": title,
        "URL": f"https://www.cpsc.gov/Recalls/{rid}", "Description": "",
        "Products": [{"Name": p} for p in products],
        "Hazards": [{"Name": "Laceration hazard"}], "Remedies": [{"Name": "Stop using"}],
        "Manufacturers": [{"Name": m} for m in (manufacturers or [])],
    }


def test_search_terms_use_full_name_then_the_product_noun():
    assert recalls.search_terms("Stainless Steel Garlic Press") == ["stainless steel garlic press", "garlic press"]
    # "(3-pack)" is dropped; a two-word name needs no second, shorter query
    assert recalls.search_terms("Ceramic Pots (3-pack)") == ["ceramic pots"]
    assert recalls.search_terms("Ceramic Plant Pots (3-pack)") == ["ceramic plant pots", "plant pots"]
    assert recalls.search_terms("") == []


def test_matches_are_possible_matches_with_verbatim_fields_and_the_disclaimer():
    fetch = lambda term: [_record(1, "Garlic Press Recalled Due to Laceration Hazard", ["Stainless Steel Garlic Press"])]
    result = recalls.check_recalls("Stainless Steel Garlic Press", fetch=fetch)
    assert result["available"] and result["provenance"] == "LIVE"
    match = result["matches"][0]
    assert match["title"] == "Garlic Press Recalled Due to Laceration Hazard"
    assert match["url"] == "https://www.cpsc.gov/Recalls/1"
    assert match["hazards"] == ["Laceration hazard"] and match["recall_date"] == "2025-04-03"
    assert "not confirmation" in result["disclaimer"]


def test_unrelated_recalls_that_share_only_one_word_are_excluded():
    fetch = lambda term: [_record(2, "Steel Water Bottles Recalled", ["Steel Bottle"])]
    result = recalls.check_recalls("Stainless Steel Garlic Press", fetch=fetch)
    assert result["available"] and result["matches"] == []  # 'steel' alone is not enough


def test_duplicates_across_queries_are_merged_and_brand_hits_sort_first():
    recs = [
        _record(3, "Garlic Press Recall", ["Garlic Press"], date="2025-06-01T00:00:00"),
        _record(4, "Garlic Press Recall B", ["Garlic Press"], date="2024-01-01T00:00:00", manufacturers=["AcmeBrand"]),
    ]
    result = recalls.check_recalls("Stainless Steel Garlic Press", "AcmeBrand", fetch=lambda term: recs)
    assert result["total_matches"] == 2  # two queries, same two records
    assert [m["recall_id"] for m in result["matches"]] == [4, 3]
    assert result["matches"][0]["brand_match"] is True


def test_unreachable_cpsc_is_reported_as_unavailable_not_as_no_recalls():
    def offline(term):
        raise URLError("blocked")

    result = recalls.check_recalls("Stainless Steel Garlic Press", fetch=offline)
    assert result["available"] is False and result["matches"] == [] and "blocked" in result["error"]


def test_results_are_cached_and_relabelled_cached():
    calls = []

    def fetch(term):
        calls.append(term)
        return []

    recalls.check_recalls("Garlic Press", fetch=fetch)
    again = recalls.check_recalls("Garlic Press", fetch=fetch)
    assert again["provenance"] == "CACHED" and len(calls) == 1
