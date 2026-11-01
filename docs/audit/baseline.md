# CommerceSense AI v3 — Baseline Audit & Repository Inspection

> **Phase 0 Baseline Inspection Report**  
> **Date:** October 31, 2026  
> **Environment:** Windows (PowerShell), Python 3.12.14, Node.js / Vite 8.3.0, React 19.2.0  
> **Repository:** `c:\Users\UPESH CHOWDARY\Desktop\sydon-1`  
> **Git Commit Baseline:** `659c2d0` ("fix: stale UI after decisions, missing pricing analyze display, silent simulator failures, missing inventory forecast chart")

---

## 1. Executive Summary

CommerceSense AI (formerly `sydon-1`) is an Amazon Seller Copilot created to monitor seller accounts, flag risks (stockouts, ad spend waste, rank drops, margin erosion, listing deficiencies), and provide mathematically verified decision support.

Prior to the commencement of **CommerceSense AI v3**, the repository successfully completed Phases 0 through 10 of its foundational development, including:
- A deterministic synthetic engine generating 60 days of metrics across 14 planted products (`data/generate_synthetic_data.py`, `data/generate_intelligence_data.py`).
- Three deterministic signal detectors (`inventory_stockout`, `ppc_waste`, `rank_drop`).
- Four deterministic intelligence modules (`listing_intelligence`, `pricing_intelligence`, `review_intelligence`, `inventory_intelligence`) and a unified `opportunity_engine`.
- Pluggable provider wrappers (`providers/llm.py`, `providers/websearch.py`, `providers/amazon_data.py`).
- A FastAPI HTTP routing layer (`api/main.py` with 13 mounted routers and 39 application endpoints).
- A React 19 + TypeScript + Vite SPA frontend with 13 client routes, Tailwind CSS v4, Lucide icons, and Recharts.

This document establishes the exact baseline state of the repository before executing Phase 1 through Phase 7 of the **CommerceSense AI v3 Free-First Master Build**.

---

## 2. Git State & Working Tree Audit

### 2.1 Git Status
- **Current Branch:** `main`
- **Head Commit:** `659c2d0` (ahead of `origin/main` by 8 local commits)
- **Recent Commit History:**
  1. `659c2d0` — fix: stale UI after decisions, missing pricing analyze display, silent simulator failures, missing inventory forecast chart
  2. `cfe2c8e` — fix: accurate Overview KPIs/charts, decision subjects, and display bugs
  3. `3de612d` — fix: restore P001 pricing data and harden CSV import against silent overwrite
  4. `a0a3b55` — chore: remove stale AUDIT_2_2026-09-23.md
  5. `55e648f` — fix: topbar horizontal overflow on mobile viewport (390px)
  6. `9e6fb8d` — fix: command palette Full Intelligence search returned no results
  4. `4a43708` — polish: format Pricing simulator result instead of dumping raw JSON
  5. `a5fe65d` — fix: track pricing/inventory simulate + inventory forecast in run_stats
  6. `120d33b` — feat: add module observability counters and wire CSV import into the UI
  7. `35bbcae` — docs: document Phase 8 gap-closing work and update README

### 2.2 Uncommitted Modifications at Baseline
- `frontend/package.json` & `frontend/package-lock.json`: `@types/node` updated to `^24.19.2`.
- `frontend/vite.config.ts`: Proxy target normalized to port `8000` (aligned with backend Uvicorn default).
- `requirements.txt`: Added `python-multipart>=0.0.9`.
- Untracked files:
  - `abc.md`: Session handoff notes.
  - `frontend/src/components/landing/HeroGlobe.tsx`: Untracked experimental 3D hero artifact from a parallel exploration.

---

## 3. Test Suite & Build Verification Record

### 3.1 Pytest Suite
Ran: `.venv\Scripts\python.exe -m pytest -v`  
- **Result:** **54 passed in 1.88s** (100% pass rate)
- **Test Modules Covered:**
  - `tests/test_activity_stats.py`: 1 test (activity stats shape and aggregation)
  - `tests/test_data_import.py`: 3 tests (template placeholders, zero-row safeguard, sample rejection)
  - `tests/test_grounding.py`: 4 tests (number fabrication rejection, verbatim number allowance, empty citation handling)
  - `tests/test_inventory_engine.py`: 10 tests (demand weighting, days of cover, safety stock, ROP, MOQ/multiple rules, inventory classification, stockout projections, simulation flags, excess inventory)
  - `tests/test_listing_engine.py`: 5 tests (scoring accuracy, failed rule reporting, deduction transparency, repeated word detection, duplicate bullet detection)
  - `tests/test_opportunity_engine.py`: 4 tests (zero score for healthy products, component sum integrity, 100-point ceiling, None-input null safety)
  - `tests/test_pricing_engine.py`: 13 tests (contribution margin, breakeven vs target ordering, unreachable target margin handling, price distribution, margin floor classification, competitive range classification, price range recommendation, contradiction downgrading, simulation math)
  - `tests/test_review_engine.py`: 14 tests (rating stats, velocity trend, verbatim review evidence, candidate word discovery, emerging issue spike threshold, category vocabularies, history insufficiency guards)

### 3.2 Evaluation Scripts
1. **Signal Detection Evaluator (`eval/run_eval.py`):**
   - 14 products evaluated against `eval/labeled_set.json` (9 planted cases, 5 healthy controls).
   - Confirmed deterministic evaluation logic executes cleanly.
2. **Intelligence Modules Evaluator (`eval/run_intelligence_eval.py`):**
   - Evaluates listing, pricing, and review classifications against `eval/labeled_set_intelligence.json`.
   - **Listing Intelligence:** TP=4, FP=0, TN=10, FN=0 → **Precision: 1.0, Recall: 1.0, F1: 1.0**
   - **Pricing Intelligence:** TP=3, FP=0, TN=11, FN=0 → **Precision: 1.0, Recall: 1.0, F1: 1.0**
   - **Review Intelligence:** TP=2, FP=2, TN=10, FN=0 → **Precision: 0.5, Recall: 1.0, F1: 0.667** (FP caused by cluster noise sensitivity on P004 and P014)

### 3.3 Frontend Build & Lint Verification
1. **TypeScript & Vite Production Build:**
   - Command: `npm --prefix frontend run build` (`tsc -b && vite build`)
   - **Result:** Exit code 0, built in 1.18s.
   - Bundle output:
     - `dist/index.html`: 1.08 kB (gzip: 0.61 kB)
     - `dist/assets/index-Bscp7G0K.css`: 37.39 kB (gzip: 7.66 kB)
     - `dist/assets/index-CCl4ddEV.js`: 1,089.35 kB (gzip: 325.32 kB)
2. **Linter (`oxlint`):**
   - Command: `npm --prefix frontend exec oxlint`
   - **Result:** 0 errors, 3 fast-refresh warnings (`button.tsx`, `badge.tsx`, `Sidebar.tsx`).

---

## 4. Current Storage & Schema Inventory

The baseline system uses two SQLite databases and one JSONL append-only file:
1. `amazon_copilot.db` (Primary SQLite database for application entities)
2. `research_cache.db` (SQLite cache for web search bundles)
3. `decisions.log.jsonl` (Append-only audit trace for all human and agent actions)

### 4.1 Database Tables in `amazon_copilot.db`
| Table Name | Primary Key | Foreign Keys | Row Count (Seeded) | Purpose |
|:---|:---|:---|:---:|:---|
| `products` | `product_id` (TEXT) | None | 14 | Catalog master record (id, name, category, base_price) |
| `daily_metrics` | `(product_id, date)` | `products.product_id` | 840 (14 × 60d) | Daily sales, inventory, rank, Buy Box, PPC spend/clicks/sales |
| `detected_signals` | `id` (INTEGER AUTO) | `products.product_id` | Variable (0-9) | Output of 3 deterministic detectors (stockout, waste, rank) |
| `listing_data` | `product_id` (TEXT) | `products.product_id` | 14 | Listing content (title, brand, bullets JSON, desc, images) |
| `listing_audits` | `id` (INTEGER AUTO) | `products.product_id` | Variable | Computed listing audit scores (0-100) and rule breakdowns |
| `listing_recommendations`| `id` (INTEGER AUTO) | `products.product_id`, `audit_id` | Variable | Title rewrite recommendations and approval status |
| `pricing_data` | `product_id` (TEXT) | `products.product_id` | 14 | Cost structure (COGS, referral fee %, FBA fee, target margin) |
| `pricing_observations` | `id` (INTEGER AUTO) | `products.product_id` | 42 (3/product) | Competitor prices, source, confidence, verification flag |
| `pricing_analyses` | `id` (INTEGER AUTO) | `products.product_id` | Variable | Financial metrics (contribution, margin %, breakeven, target) |
| `review_items` | `id` (INTEGER AUTO) | `products.product_id` | 280 (20/product) | Individual customer reviews (rating, text, date, verified) |
| `review_analyses` | `id` (INTEGER AUTO) | `products.product_id` | Variable | Review stats, velocity, themes JSON, emerging issues JSON |
| `inventory_config` | `product_id` (TEXT) | `products.product_id` | 14 | Supply chain settings (lead time, safety days, MOQ, multiple) |
| `intelligence_runs` | `id` (INTEGER AUTO) | `products.product_id` | Variable | Module execution tracker for observability (started, finished, status) |

### 4.2 SQLite Indexes
- `idx_listing_audits_product` ON `listing_audits(product_id)`
- `idx_pricing_observations_product` ON `pricing_observations(product_id)`
- `idx_review_items_product` ON `review_items(product_id)`
- `idx_review_items_date` ON `review_items(review_date)`
- `idx_intelligence_runs_product` ON `intelligence_runs(product_id)`
- `idx_intelligence_runs_module` ON `intelligence_runs(module)`

---

## 5. Existing Backend API Route Inventory

The FastAPI server mounts 29 endpoints across 13 modules under the `/api` prefix:

| Method | Endpoint Path | Router File | Current Provenance | Description |
|:---|:---|:---|:---:|:---|
| `GET` | `/api/health` | `api/main.py` | CALCULATED | System health, API key presence booleans, feature flag status |
| `GET` | `/api/products` | `api/routers/products.py` | SYNTHETIC | List all products with inlined cross-module health summaries |
| `GET` | `/api/products/{id}` | `api/routers/products.py` | SYNTHETIC | Single product detail with daily metrics and recent signals |
| `POST` | `/api/signals/run` | `api/routers/signals.py` | SYNTHETIC | Clear and re-run all 3 deterministic signal detectors |
| `GET` | `/api/signals` | `api/routers/signals.py` | SYNTHETIC | List detected signals with optional severity/type filters |
| `GET` | `/api/signals/{id}` | `api/routers/signals.py` | SYNTHETIC | Get single signal detail and historical context |
| `POST` | `/api/research` | `api/routers/research.py` | LIVE / CACHED | Trigger live web research via Tavily + Gemini query planner |
| `GET` | `/api/research/cached` | `api/routers/research.py` | CACHED | Read-only fetch of cached research bundle without live API calls |
| `POST` | `/api/intelligence` | `api/routers/intelligence.py` | LIVE | Full research + grounded insight generation pipeline |
| `POST` | `/api/decisions` | `api/routers/decisions.py` | SELLER_INPUT | Record human approval/rejection into `decisions.log.jsonl` |
| `GET` | `/api/decisions` | `api/routers/decisions.py` | SELLER_INPUT | Query historical decisions filtered by product or action |
| `GET` | `/api/evaluation` | `api/routers/evaluation.py` | CALCULATED | Run live evaluation of signal and intelligence detectors |
| `GET` | `/api/agents` | `api/routers/agents.py` | CALCULATED | Agent status, LLM invocation counters, run statistics |
| `GET` | `/api/activity` | `api/routers/agents.py` | CALCULATED | Read raw events from `decisions.log.jsonl` |
| `GET` | `/api/activity/stats` | `api/routers/agents.py` | CALCULATED | Aggregate action counts and per-agent metrics from trace log |
| `GET` | `/api/listing-intelligence/{id}` | `api/routers/listing_intelligence.py` | SYNTHETIC | Get stored listing data and latest audit results |
| `POST` | `/api/listing-intelligence/{id}/analyze` | `api/routers/listing_intelligence.py` | CALCULATED | Evaluate listing against rules and generate Ollama explanation |
| `POST` | `/api/listing-intelligence/{id}/rewrite` | `api/routers/listing_intelligence.py` | MODELLED | Propose AI title rewrite with strict grounding check |
| `POST` | `/api/listing-intelligence/{id}/approve` | `api/routers/listing_intelligence.py` | SELLER_INPUT | Approve/reject listing title rewrite |
| `GET` | `/api/pricing-intelligence/{id}` | `api/routers/pricing_intelligence.py` | SYNTHETIC | Financial unit economics, competitor spread, price state |
| `POST` | `/api/pricing-intelligence/{id}/analyze` | `api/routers/pricing_intelligence.py` | CALCULATED | Calculate contribution margins, breakeven, recommendation |
| `POST` | `/api/pricing-intelligence/{id}/simulate` | `api/routers/pricing_intelligence.py` | CALCULATED | What-if price simulator evaluating margin impact |
| `POST` | `/api/pricing-intelligence/{id}/approve` | `api/routers/pricing_intelligence.py` | SELLER_INPUT | Approve/reject recommended price changes |
| `GET` | `/api/review-intelligence/{id}` | `api/routers/review_intelligence.py` | SYNTHETIC | Rating distributions, velocity, themes, emerging issues |
| `POST` | `/api/review-intelligence/{id}/analyze` | `api/routers/review_intelligence.py` | CALCULATED | Extract themes, detect emerging spikes, cluster semantics |
| `GET` | `/api/inventory-intelligence/{id}` | `api/routers/inventory_intelligence.py` | SYNTHETIC | Days of cover, reorder point, safety stock, suggested reorder |
| `POST` | `/api/inventory-intelligence/{id}/analyze` | `api/routers/inventory_intelligence.py` | CALCULATED | Analyze inventory health category and stockout date |
| `POST` | `/api/inventory-intelligence/{id}/simulate` | `api/routers/inventory_intelligence.py` | CALCULATED | Reorder scenario simulator (lead time vs reorder quantity) |
| `GET` | `/api/inventory-intelligence/{id}/forecast` | `api/routers/inventory_intelligence.py` | MODELLED | Projected 60-day inventory burn chart with inbound shipment |
| `GET` | `/api/products/{id}/intelligence` | `api/routers/opportunity.py` | CALCULATED | Unified Commerce Attention Score synthesizing all 4 modules |
| `GET` | `/api/data-import/template/{type}` | `api/routers/data_import.py` | CALCULATED | Download CSV starter template for a data type |
| `POST` | `/api/data-import/{type}/validate` | `api/routers/data_import.py` | CALCULATED | Validate uploaded CSV and return row-by-row error report |
| `POST` | `/api/data-import/{type}/commit` | `api/routers/data_import.py` | SELLER_INPUT | Commit validated CSV rows into SQLite database |

---

## 6. Existing Frontend Routes & Architecture

### 6.1 Route Mapping (`frontend/src/App.tsx`)
1. `/` — `Landing.tsx` (CSS 3D cube hero, architecture diagrams)
2. `/overview` — `Overview.tsx` (KPIs, Attention leaderboard, charts, recent signals)
3. `/products` — `Products.tsx` (Product catalog list, filter badges, search)
4. `/products/:productId` — `ProductDetail.tsx` (Detail view with inline module tabs)
5. `/products/:productId/intelligence` — `ProductIntelligence.tsx` (Full bundle view, Attention score breakdown)
6. `/signals` — `Signals.tsx` (Signal list and filters)
7. `/signals/:signalId` — `SignalDetail.tsx` (Deep dive into detected signal evidence)
8. `/research` — `Research.tsx` (Web search tool and findings history)
9. `/agents` — `Agents.tsx` (Agent status, observability metrics, run counts)
10. `/decisions` — `DecisionCenter.tsx` (Pending and recorded human approval queue)
11. `/evaluation` — `Evaluation.tsx` (Precision/recall/F1 test matrix and planted cases)
12. `/activity` — `Activity.tsx` (Centralized decision log event stream)
13. `/settings` — `Settings.tsx` (API keys, CSV import tool, configuration)

### 6.2 Frontend Technology Baseline
- **Build tool:** Vite 8.3.0 with `@vitejs/plugin-react`
- **Framework:** React 19.2.0, React DOM 19.2.0
- **Routing:** React Router DOM 7.13.0
- **Server State:** TanStack React Query 5.67.1
- **Styling:** Tailwind CSS 4.3.3 (`@tailwindcss/vite`), `clsx`, `tailwind-merge`
- **Icons:** `lucide-react` 1.16.0
- **Charts:** `recharts` 3.7.0
- **Primitives:** Radix UI (`@radix-ui/react-tabs`, `@radix-ui/react-slot`, `cmdk`)

---

## 7. Gap Analysis: Baseline vs. CommerceSense AI v3

Comparing the baseline codebase against the requirements of the **Master Build Prompt v3** and **UI/UX Redesign Prompt v3** reveals the following architectural and functional gaps to be addressed in subsequent phases:

| Capability / Requirement | Current Baseline State | CommerceSense AI v3 Target (Phases 1-7) | Phase Addressing |
|:---|:---|:---|:---:|
| **Database Architecture** | SQLite (`amazon_copilot.db`), no schema versioning | PostgreSQL 16+ with Alembic migrations + one-time SQLite data migration | Phase 1 |
| **Free-First Policy Gate** | Soft flags (`LLM_PROVIDER`, `ENABLE_SEARXNG`); Tavily and Gemini are directly reachable if keys are set | Strict `FREE_ONLY=true` hard network gate blocking all paid external API endpoints (Tavily, Keepa, SerpAPI, hosted LLMs) | Phase 1 |
| **Provenance Envelope** | Ad-hoc string labels (`SYNTHETIC`, `LIVE`, `CACHED`, `DEMO`) | Universal 8-category provenance source envelope on every payload: `AMAZON_OFFICIAL`, `PUBLIC_NEWS`, `SELLER_INPUT`, `CALCULATED`, `MODELLED`, `CACHED`, `DEMO`, `MISSING` | Phase 1 |
| **Local LLM Integration** | Basic Ollama HTTP helper with JSON schema format | Robust Ollama adapter with health checking, model autodetection (`qwen3-vl`, `llama3.2`), and 100% deterministic fallback | Phase 1 |
| **Task Queue** | Synchronous requests with threading locks (`threading.Lock`) | Async task queue (Chancy or Celery+Valkey/Redis) for background SP-API report polling and batch forecasting | Phase 1 |
| **Amazon SP-API Connector** | Documented stub raising `NotImplementedError` | Official SP-API SDK (`amzn-sp-api`), EU endpoint (`sellingpartnerapi-eu.amazon.com`) for Amazon.in (`A21TJRUUN4KGV`), LWA OAuth token refresh, Reports API | Phase 2 |
| **Competitor Intelligence** | Static seeded observations (3 per product) | SP-API `getCompetitiveSummary` batching, prospective PostgreSQL price snapshots, 3-tier matching (Same ASIN, Equivalent, Substitute) | Phase 3 |
| **Pricing Engine Precision** | Standard Python `float` arithmetic | High-precision `decimal.Decimal` financial calculations, closing fees, referral fee tiers, DO_NOT_MATCH rules, margin floors | Phase 3 |
| **Market Radar & Brand Analytics**| Not implemented | GDELT 2.0 Doc API (public global news), Category RSS feeds, Google Trends CSV parser, Brand Analytics search terms | Phase 4 |
| **Demand Forecasting** | Simple historical weighted average (7d/14d/30d) | `StatsForecast` integration (AutoARIMA, Croston, SBA, Naive) with stockout-censored demand adjustment | Phase 5 |
| **Durable Automation Engine** | Manual approval endpoints only | Automation rules engine with persistent condition evaluation, safety bounds, and Action Center approval queue | Phase 5 |
| **UI/UX Art Direction** | Dark-first developer dashboard with neon accents | "The Seller Control Room" — Light-first default B2B SaaS, restrained forest/sage accents (`#1B4332`, `#2D6A4F`, `#52B788`), high data density | Phase 6 |
| **Core Navigation Routes** | 13 mixed developer/demo routes | 11 unified core operator routes (Overview, Portfolio, Workspace, Competitor Watch, Market Radar, Opportunities, Pricing Lab, Action Center, Automations, Research Reports, Settings) | Phase 6 |
| **Security & Privacy** | Plain environment variables, unencrypted cache | AES-256 credential encryption at rest, egress filtering, strict zero Amazon scraping compliance | Phase 7 |

---

## 8. Baseline Verification Sign-Off

- [x] All 54 unit and engine tests pass cleanly.
- [x] Evaluator scripts run and report accurate metrics.
- [x] Frontend builds cleanly with zero errors.
- [x] All existing database tables, routes, and components cataloged.
- [x] Zero application logic modified during Phase 0 audit.
- [x] Baseline established and documented for Phase 1 execution.

