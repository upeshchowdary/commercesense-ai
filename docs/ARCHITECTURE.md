# CommerceSense AI v3 — System Architecture

> **Architecture Document:** `docs/ARCHITECTURE.md`  
> **Status:** Canonical Specification  
> **Target Version:** CommerceSense AI v3  

---

## 1. System Topology Overview

CommerceSense AI v3 is structured as a decoupled, multi-tier system designed for high data density, zero paid API dependencies, and strict Amazon compliance.

```
+==================================================================================================+
|                                    COMMERCESENSE AI v3 TOPOLOGY                                  |
+==================================================================================================+

   +--------------------------------------------------------------------------------------------+
   |                                 PRESENTATION LAYER                                         |
   |   React 19 + TypeScript + Vite | Tailwind CSS v4 | Recharts | Radix UI | Lucide React        |
   |                                                                                            |
   |   11 Control Room Routes:                                                                  |
   |   [Overview] [Portfolio] [Workspace (7 Tabs)] [Competitor Watch] [Market Radar]            |
   |   [Opportunities] [Pricing Lab] [Action Center] [Automations] [Reports] [Settings]         |
   +---------------------------------------------+----------------------------------------------+
                                                 | HTTP / SSE (Port 8000)
                                                 v
   +--------------------------------------------------------------------------------------------+
   |                               APPLICATION & ROUTING LAYER                                  |
   |   FastAPI Application (api/main.py) | Dependency Injection | Pydantic v2 Schemas           |
   |                                                                                            |
   |   +------------------------------------------------------------------------------------+   |
   |   | FREE_ONLY Hard Gate Middleware (Blocks paid API calls; enforces egress allowlist)  |   |
   |   +------------------------------------------------------------------------------------+   |
   |                                                                                            |
   |   Routers: /products, /signals, /listing, /pricing, /review, /inventory, /opportunity,    |
   |            /competitors, /radar, /forecast, /actions, /automations, /reports, /settings    |
   +---------------------------------------------+----------------------------------------------+
                                                 |
         +---------------------------------------+---------------------------------------+
         |                                                                               |
         v                                                                               v
+-----------------------------------+                           +-----------------------------------+
|     CORE DETERMINISTIC ENGINES    |                           |      BACKGROUND TASK RUNNER       |
| (Pure Python, Zero External Deps) |                           | (Chancy / Celery + Valkey Fallback|
|                                   |                           |                                   |
| • Pricing Engine (Decimal Math)   |                           | • SP-API Report Poller            |
| • Inventory Engine (Days of Cover)|                           | • StatsForecast Batch Runner      |
| • Listing Engine (Quality Rules)  |                           | • GDELT & RSS Ingestion Worker    |
| • Review Engine (Vocabulary/Spike)|                           | • Automation Rules Evaluator      |
| • Opportunity Engine (Attention)  |                           +-----------------+-----------------+
| • Automation Rules Engine         |                                             |
+-----------------+-----------------+                                             |
                  |                                                               |
                  +-------------------------------+-------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                  DATA ACCESS & PERSISTENCE LAYER                                  |
|   PostgreSQL 16+ (Primary Relational Store) | SQLAlchemy 2.0 Core | Alembic Migrations            |
|   * Tables: products, daily_metrics, detected_signals, listing_audits, pricing_snapshots,         |
|             competitor_observations, review_analyses, inventory_snapshots, automation_rules,      |
|             action_queue, provenance_registry                                                     |
|                                                                                                   |
|   Append-Only Decision Log: decisions.log.jsonl / postgres_decision_log (Immutable Audit Trail)    |
|   Local Cache Store: SQLite/Redis TTL Cache (Web findings, report artifacts)                     |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                     EXTERNAL PROVIDER BOUNDARY                                    |
|                                                                                                   |
|  [FREE & OFFICIAL ONLY]                                                                           |
|  • Official Amazon SP-API SDK (amzn-sp-api): EU Endpoint (sellingpartnerapi-eu.amazon.com)        |
|    Marketplace: Amazon.in (A21TJRUUN4KGV) | Reports, Catalog, Listings, Pricing APIs              |
|  • Public News Intelligence: GDELT 2.0 Doc API (api.gdeltproject.org)                             |
|  • Public Feeds: Python feedparser / httpx for Category & Regulatory RSS Feeds                    |
|  • Local Inference: Ollama REST Adapter (http://localhost:11434) with JSON Schema Constraints   |
|  • Time-Series Forecasting: StatsForecast (AutoARIMA, Croston, SBA, HistoricAverage)             |
|  • Seller Data Imports: CSV Validation & Ingestion Engine (Multi-Part Uploads)                    |
|                                                                                                   |
|  [STRICTLY PROHIBITED & BLOCKED]                                                                  |
|  x Tavily, SerpAPI, Perplexity | x Keepa, Sorftime, Apify | x Hosted LLMs (OpenAI, Anthropic)     |
+===================================================================================================+
```

---

## 2. Backend Architecture

### 2.1 Web Framework & Router Topology
The backend is built on **FastAPI** running under **Uvicorn**, using asynchronous route handlers where beneficial and synchronous threadpools for CPU-intensive mathematical calculations.

Directory Structure:
```
api/
  main.py                     # FastAPI application setup, middleware, lifecycle events
  deps.py                     # Database sessions, provider injection, user context
  schemas.py                  # Pydantic v2 request/response contracts with Provenance
  intelligence_common.py      # Shared explanation/graceful degradation helpers
  routers/
    products.py               # Product portfolio & workspace endpoints
    signals.py                # Deterministic signal detection runs & listings
    listing_intelligence.py   # Listing audit, scoring, and title rewrites
    pricing_intelligence.py   # Cost-complete pricing, margin simulator, approval
    review_intelligence.py    # Rating stats, themes, velocity, emerging spikes
    inventory_intelligence.py # Days of cover, safety stock, ROP, what-if burn
    opportunity.py            # Unified Commerce Attention Score
    competitor_watch.py       # 3-tier competitor snapshots, Buy Box radar
    market_radar.py           # GDELT news, RSS digest, macro trend indicators
    forecasting.py            # StatsForecast time-series demand projections
    action_center.py          # Unified operator approval/rejection queue
    automations.py            # Durable rule management and execution logs
    research_reports.py       # Weekly brief generation & PDF/Markdown export
    data_import.py            # Standardized CSV template, validate, commit
    settings.py               # SP-API credentials check, Ollama diagnostics
```

### 2.2 Database & Persistence Architecture
CommerceSense AI v3 transitions from a local SQLite prototype database to a robust relational model powered by **PostgreSQL 16+** with **SQLAlchemy 2.0** and **Alembic** for schema migrations.

1. **One-Time Safe SQLite Migration:**
   - A dedicated migration script (`db/migrate_sqlite_to_pg.py`) reads the existing `amazon_copilot.db` tables, maps columns, converts floating-point currency values to `DECIMAL(12, 4)`, and inserts all existing products, metrics, and audits into PostgreSQL idempotently.
2. **Schema Versioning via Alembic:**
   - All migrations are tracked under `db/alembic/` with strict upgrade and downgrade pathways.
3. **Decoupled Audit Trace:**
   - All human approvals, rejections, rule triggers, and provider invocations write to `decisions.log.jsonl` and mirror into a dedicated `audit_events` table in PostgreSQL.

### 2.3 Background Queue & Asynchronous Execution
Long-running operations—such as Amazon SP-API report generation (which can take 1–15 minutes for Amazon to produce), heavy StatsForecast model fitting, and GDELT news ingestion—must never block HTTP request threads.

- **Primary Task Queue:** **Chancy** (a modern, lightweight PostgreSQL-backed task queue with native concurrency control and retry logic).
- **Fallback / Alternative:** **Celery** backed by **Valkey** (the open-source Redis fork) or Redis.
- **Worker Process:** `worker/run_worker.py` polling for background tasks:
  * `tasks.sp_api.fetch_sales_traffic_report`
  * `tasks.sp_api.fetch_inventory_report`
  * `tasks.forecasting.fit_demand_models`
  * `tasks.radar.ingest_gdelt_news`
  * `tasks.automations.evaluate_rules`

---

## 3. Provider Architecture & Free-First Hard Gate

### 3.1 Network Egress Filter & Hard Gate
To enforce the **FREE_ONLY=true** policy, CommerceSense AI implements an application-level egress interceptor (`providers/gate.py`):
- Any outgoing HTTP call via `httpx`, `requests`, or `urllib` is checked against an **Approved Domain Allowlist**:
  * `sellingpartnerapi-eu.amazon.com` (Official Amazon SP-API EU Endpoint)
  * `api.amazon.com` (Amazon LWA Token Exchange)
  * `api.gdeltproject.org` (GDELT 2.0 Doc API)
  * `news.google.com` (Public RSS News Feeds)
  * `localhost` / `127.0.0.1` (Local Ollama, PostgreSQL, Valkey)
- Any attempt to reach unapproved domains (e.g., `api.tavily.com`, `api.keepa.com`, `api.openai.com`, `api.anthropic.com`) raises an immediate `FreeFirstPolicyViolationError` and fails closed.

### 3.2 Amazon SP-API Connector Architecture
- **Library:** Official `amzn-sp-api` Python SDK (or official Amazon SP-API REST interface).
- **Target Marketplace:** Amazon.in (`MarketplaceId: A21TJRUUN4KGV`).
- **Endpoint:** EU Host (`sellingpartnerapi-eu.amazon.com`).
- **Authentication:** Login with Amazon (LWA) refresh-token exchange yielding ephemeral access tokens (cached for 3,600s).
- **Core Endpoints Implemented:**
  1. `Reports API`: Request, poll, and parse `GET_SALES_AND_TRAFFIC_REPORT` and `GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA`.
  2. `Product Pricing API`: `getCompetitiveSummary` (batched up to 20 ASINs per call) to retrieve Buy Box price, lowest offers, and sales ranks.
  3. `Listings Items API`: `getListingsItem` to fetch listing title, bullet points, attributes, and fulfillment details.
  4. `Brand Analytics API`: `GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT` for search frequency rank and click-share data.
- **Rate-Limiting & Backoff:** Token-bucket rate limiter implementing Amazon’s specified quotas with exponential jitter backoff on HTTP 429.

### 3.3 Free Market Radar Provider
- **GDELT 2.0 Doc API:** Ingests articles via query: `https://api.gdeltproject.org/api/v2/doc/doc?query={category_keywords}&mode=ArtList&maxrecords=25&format=json`. Extracts article headline, source domain, publication time, and sentiment score.
- **RSS Syndication Engine:** Polls public category feeds using `feedparser`, stripping HTML tags and caching articles locally.
- **Google Trends CSV Parser:** Ingests exported trend search interest series without automated scraping.

### 3.4 Local LLM Adapter (Ollama)
- **Protocol:** HTTP REST to `http://localhost:11434/api/generate`.
- **Structured Output:** Enforces Pydantic schemas via Ollama’s `format` parameter.
- **Quirk Mitigation:** Handles dual-channel output (checking `response` first, falling back to `thinking` for reasoning-oriented models like `qwen3-vl`).
- **Deterministic Fallback:** If Ollama returns a non-200 status, times out, or fails schema validation, the adapter returns `available: false` with the fallback deterministic analysis intact.

---

## 4. Frontend Architecture

### 4.1 React Single-Page Application (SPA)
- **Framework:** React 19.2.0 with TypeScript in strict mode (`tsc -b`).
- **Build System:** Vite 8.3.0 with Rollup-based chunking.
- **Router:** React Router DOM v7 providing route-level code splitting via `React.lazy`.
- **Server Cache:** TanStack React Query v5 with 60-second stale times and optimistic updates for operator decisions.

### 4.2 UI Design System & Component Library
- **CSS Engine:** Tailwind CSS v4 using CSS variable tokens.
- **Color Identity:** "The Seller Control Room" — Calm forest/sage palette (`#1B4332`, `#2D6A4F`, `#52B788`, `#D8F3DC`), crisp high-contrast text, light-first default with dark mode support.
- **Visual Atoms:** Radix UI primitives (`@radix-ui/react-tabs`, `@radix-ui/react-slot`, `cmdk` for command palette).
- **Data Visualization:** Recharts (responsive line, bar, area, and scatter charts).
- **Iconography:** Lucide React icons.

### 4.3 Responsive Viewport Strategy
1. **Desktop (1440px+):** Full data density. 4-column KPI grids, side-by-side data tables and charts, permanent sidebar navigation.
2. **Tablet / Compact (1024px):** 2-column KPI grids, collapsible sidebar, horizontally scrollable data tables.
3. **Mobile (390px):** Single-column layout, bottom navigation drawer / sheet menu, truncated badges, card-based table representations, zero horizontal page overflow.

---

## 5. State Machines & Workflows

### 5.1 Action Center Lifecycle State Machine
Every system recommendation (price adjustment, title rewrite, purchase order reorder) transitions through an explicit lifecycle:

```
+---------------+
|   DETECTED    |  (Engine computes recommendation from live/synthetic data)
+-------+-------+
        |
        v
+---------------+
|    QUEUED     |  (Enters Action Center with full "Why Panel" evidence)
+-------+-------+
        |
        +-----------------------------------------------+
        |                       |                       |
        v                       v                       v
+---------------+       +---------------+       +---------------+
|   APPROVED    |       |   REJECTED    |       |    SNOOZED    |
| (Human clicks |       | (Human clicks |       | (Muted for    |
|   Approve)    |       | Reject + notes|       |   7 Days)     |
+-------+-------+       +---------------+       +-------+-------+
        |                                               |
        v                                               v
+---------------+                               +---------------+
|   EXECUTED    |                               |   RE-EVAL     |
| (SP-API call  |                               | (Re-enters    |
|  or CSV export|                               |  queue after  |
|   logged)     |                               |  snooze TTL)  |
+---------------+                               +---------------+
```

### 5.2 Signal Detection Pipeline Lifecycle
1. **Extraction:** Worker fetches latest 60-day metrics for all catalog products.
2. **Deterministic Rules Evaluation:**
   - `inventory_signal`: Checks days of stock against threshold (10 days).
   - `ppc_waste_signal`: Evaluates ad spend without sales or ACOS > 60%.
   - `rank_bb_signal`: Detects 3-consecutive-day rank drop or Buy Box loss.
3. **Trace Recording:** Appends detected signals to `detected_signals` table and logs event to `decisions.log.jsonl`.
4. **Attention Score Aggregation:** `opportunity_engine` recomputes the unified 0–100 Attention Score for affected products.
5. **SSE Notification:** Server-Sent Events stream notify active frontend sessions to refetch queries.

