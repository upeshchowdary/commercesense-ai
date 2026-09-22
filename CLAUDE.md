
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
- [ ] Phase 5  Streamlit UI
- [ ] Phase 6  Eval scripts + LIVE/PLANNED table + speaker script
