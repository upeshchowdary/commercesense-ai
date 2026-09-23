
# sydon-1  Amazon Seller Copilot (CUBE Buildathon practice project)

This file is the persistent project memory. Read it at the start of
every phase and follow it. Update "Phase status" at the end of each
phase.

## What this project is

A practice build for the CUBE Buildathon (Sydon AI / CodeQuesters,
2026)  hands-on reps with agentic tool-use, grounding, and human
approval before the real problem statement is announced. Domain: an AI
copilot for Amazon sellers.

One-sentence outcome: "Flag which of my products need attention this
week  stockout, wasted ad spend, falling rank, or policy/market
risk  and tell me why, before it costs me money."

## Environment notes

- Confirmed working Python version: 3.12.14.
- The project `.venv` was rebuilt once in this session against Python 3.12.
- If imports fail with `ModuleNotFoundError`, the venv likely needs a rebuild;
  check `.venv\Scripts\python.exe --version` before assuming source code is
  broken.

## Architecture  two halves that must never mix

1. SYNTHETIC side  3 deterministic signal detectors (inventory
   stockout, PPC waste, rank/Buy Box movement) reading FAKE
   seller-account data generated locally. No live calls. Runs
   automatically.

2. LIVE side  two agents calling real APIs:
   - Agent 5 (Research Agent)  searches the live web for a product via
     Tavily, returns raw structured findings, draws no conclusions.
   - Agent 6 (Insight Agent)  reads Agent 5's findings and produces
     grounded insights (pricing, trend, risk, opportunity) via Gemini.
     NEVER runs automatically  only on a human clicking a button.

## Standing rules  apply to every phase, always

1. Never invent credentials. If any API key, login, or auth is needed
   and isn't already in .env, STOP and ask the user.
2. Only Tavily and Gemini (`google-genai`) are available. No Anthropic
   key exists  never call the Anthropic/Claude API at runtime here.
3. Never claim something works without having actually run it.
4. Grounding is non-negotiable for Agent 6  every insight with
   confidence above "none" must cite a source_snippet that actually
   appears in Agent 5's findings.
5. LIVE vs FAKE must be visually distinguishable everywhere.
6. Decision tracing is shared  everything logs through
   `agent/decision_log.py`, never a second mechanism.

## Phase status

- [x] Phase 0  Scaffold + contracts
- [x] Phase 1  Agent 5 (Research Agent, Gemini + Tavily)  redesigned from AFC to structured-output query planning because Gemini AFC did not reliably call web_search
- [x] Phase 2  Agent 6 (Insight Agent, grounding-enforced)
- [x] Phase 3  Orchestrator + live end-to-end test — cold-start Samsung Galaxy Buds3 Pro passed; cache-hit (research) + live-run (insight) split confirmed on second call; load_dotenv added to both agent modules so `python orchestrator.py` works without pre-exporting vars
- [x] Phase 4  Synthetic data + 3 deterministic signals  14 products/60 days each, seeded (SEED=42) generator writes ground truth to eval/labeled_set.json; all 3 detectors cross-checked clean against planted labels (9/9 planted cases detected, 0 false positives on healthy controls). Also fixed decision_log.py/cache_store.py CWD-relative path bug (committed separately) before starting  both anchored to project root now, existing log/cache migrated from agent/ with history intact
- [x] Phase 5  UI rebuilt as React/TypeScript/Vite (Streamlit removed by user request, mid-Phase-5-Part-A). New `api/` FastAPI layer (additive only, no agent/signal logic duplicated) wraps every backend entry point: products, signals (run + list, concurrency-locked), research (Agent 5, cache-hit introspection using the agent's own TTL constant), intelligence (calls `orchestrator.run_market_intelligence_with_evidence`, no duplicated pipeline logic), decisions (human-in-the-loop endpoint, logged via decision_log.py), evaluation (eval/run_eval.py implemented for real), agents (status derived from decision_log.py, one log read per request). All request bodies/query params validated (empty/short product names, bad severity/type/category all 422; missing GEMINI_API_KEY or an agent exception is 503/502, never a bare 500). `agent/insight_agent.py` gained a second grounding guardrail (`_apply_source_match_guardrail`) that requires a cited snippet to literally appear in Agent 5's findings, not just be non-empty — verified offline with a fabricated-citation test. `agent/research_agent.py`'s DuckDuckGo fallback removed (standing rule 2); failed/missing searches now log and drop instead of returning fake findings. Full React frontend built: Landing (3D CSS cube hero + pipeline flow) + all 9 nav pages (Overview, Products, Product Detail, Signals, Signal Detail, Research, AI Agents, Decision Center, Evaluation, Activity, Settings) + a real guided Demo Mode overlay + a command palette searching products/signals/pages. Every data surface carries a LIVE/CACHED/SYNTHETIC/DEMO badge. `npm run build` and `npx oxlint` both clean; backend smoke-tested via FastAPI TestClient (18/18 checks) and two real live Gemini+Tavily runs (cache-miss then cache-hit, 4/4 insights grounded) through the running server. Human visual sign-off in a real browser still recommended — no browser-automation tool was available in this session to click through it directly.
- [x] Phase 6 (partial)  `eval/run_eval.py` implemented for real: live comparison of eval/labeled_set.json against current detected_signals, exposed via GET /api/evaluation and a CLI entry point; now also counts an unrelated/extra signal type on a planted product as a false positive, not just a missed expected one. Still open: a LIVE/PLANNED capability table and a speaker script for the demo — not attempted here, needs presentation context (timing, audience) not established in this file.
- [x] Phase 7  Four intelligence modules added (Listing, Pricing, Review, Inventory Intelligence) plus a Commerce Opportunity Engine, extending — never replacing — the existing product model, decision log, and cache. New `intelligence/` package (pure, deterministic, unit-tested engines — 45 pytest tests, all passing), new `providers/` package (pluggable LLM via Ollama — verified working locally, real structured JSON output, including handling a real quirk where the qwen3-vl model family returns schema-constrained output in the `thinking` field instead of `response` even with `think:false` — or Gemini; web-search reuses the existing Research Agent, not a second engine; SP-API is a documented interface stub only, never a fake success, since no real credentials exist to verify against). New `db/intelligence_db.py` + schema additions (all FK'd to `products.product_id`, no new product model). New synthetic data (`data/generate_intelligence_data.py`, same SEED=42, deterministic planted ground truth in `eval/labeled_set_intelligence.json`) and a real evaluator (`eval/run_intelligence_eval.py`, precision/recall/F1 per module — Listing and Pricing both 1.0/1.0/1.0, Review recall 1.0 / precision 0.4 after two rounds of fixing genuine bugs found via testing: a pricing-margin generator bug that made "healthy" products fail their own target, and review emerging-issue detection being too sensitive to random date-clustering noise — the remaining Review precision gap is reported honestly, not hidden). New `api/routers/{listing,pricing,review,inventory}_intelligence.py`, `opportunity.py` (`GET /api/products/{id}/intelligence`, the Attention Score), and `data_import.py` (CSV template/validate/commit, no Amazon API required). Frontend: new `/products/:id/intelligence` Product Bundle View page (tabs per module, AI rewrite with a live grounding check, price/inventory simulators, human approve/reject wired to the existing decision log), linked from Products and Product Detail; Evaluation page extended with the new module metrics. One real regression caught and fixed along the way: `gemini-2.5-flash` (the old code default in `research_agent.py`/`insight_agent.py`) is now deprecated by Google — default updated to `gemini-3.6-flash` (the actually-configured `.env` model, `gemini-3.5-flash-lite`, was unaffected and still works). `npm run build` and `npx oxlint` clean; Playwright-verified zero console errors on the new page and tabs.
