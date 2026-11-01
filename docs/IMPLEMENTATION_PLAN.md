# CommerceSense AI v3 — Implementation Plan & Phase Roadmap

> **Implementation Roadmap:** `docs/IMPLEMENTATION_PLAN.md`  
> **Status:** Canonical Engineering Plan  
> **Target Version:** CommerceSense AI v3  

---

## 1. Roadmap Overview & Dependency Graph

The transformation of CommerceSense AI into **v3 (The Seller Control Room)** is executed across eight strictly sequenced phases (Phase 0 through Phase 7). Each phase builds on verified contracts from preceding phases, ensuring no regressions, no premature architectural changes, and zero data corruption.

```
+==================================================================================================+
|                                    PHASE DEPENDENCY GRAPH                                        |
+==================================================================================================+

   [PHASE 0: Audit & Contracts]  <--- (Baseline Inspection, Specifications, Methodology)
               |
               v
   [PHASE 1: Free-First Foundations] <--- (PostgreSQL, Alembic, FREE_ONLY Gate, Ollama, Queue)
               |
               v
   [PHASE 2: Amazon SP-API Connector] <--- (amzn-sp-api, Sales/Traffic, Inventory, Capability Matrix)
               |
               v
   [PHASE 3: Competitor & Pricing Engine] <--- (getCompetitiveSummary, Decimal Math, Floor Protection)
               |
               v
   [PHASE 4: Market Radar & Brand Analytics] <--- (GDELT, RSS, Brand Analytics, Opportunity Scoring)
               |
               v
   [PHASE 5: Forecasting & Automation] <--- (StatsForecast, Croston, Uncensoring, Durable Rules)
               |
               v
   [PHASE 6: UI/UX "The Seller Control Room"] <--- (11 Core Routes, Light-First, Forest/Sage Tokens)
               |
               v
   [PHASE 7: Security, Hardening & Verification] <--- (AES-256, End-to-End Test Matrix, Benchmarks)
```

---

## 2. Phase-by-Phase Execution Details

### Phase 0: Audit & Contracts (CURRENT PHASE)
- **Objective:** Establish the comprehensive baseline of the repository, execute full test suites, and write complete specification and methodology contracts before touching application logic.
- **Key Tasks:**
  1. Inspect Git status, tests, and build artifacts.
  2. Verify existing pytest suite (54 passed) and evaluation scripts.
  3. Create baseline audit report (`docs/audit/baseline.md`).
  4. Author core specifications: `PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`, `docs/PRICING_METHODOLOGY.md`, `docs/FORECASTING_METHODOLOGY.md`, `docs/SECURITY_AND_PRIVACY.md`, `docs/IMPLEMENTATION_PLAN.md`, and `DESIGN.md`.
  5. Map every metric, field, and route to its provenance envelope.
- **Entry Criteria:** Clean repository checkout on branch `main`.
- **Exit Criteria:** All specification documents created; test suite confirmed passing; zero destructive code changes.

---

### Phase 1: Free-Only Infrastructure & Data Foundations
- **Objective:** Stand up robust, scalable data persistence and enforce the strict Free-First policy boundary.
- **Key Tasks:**
  1. **PostgreSQL 16+ Setup & SQLAlchemy 2.0 Integration:** Configure relational database models mirroring the catalog, metrics, audits, and observations.
  2. **Alembic Migration Pipeline:** Initialize migration environment (`db/alembic/`) with baseline versioning.
  3. **Idempotent SQLite to PostgreSQL Migration Script:** Build `db/migrate_sqlite_to_pg.py` to safely migrate existing SQLite data into PostgreSQL with decimal conversion.
  4. **Strict `FREE_ONLY=true` Egress Hard Gate:** Implement network interceptor (`providers/gate.py`) rejecting outbound traffic to unapproved domains (Tavily, Keepa, SerpAPI, OpenAI).
  5. **Standardized Provenance Source Envelope:** Wrap all API response models in Pydantic models carrying the 8 standardized provenance tags.
  6. **Local Ollama Adapter Hardening:** Implement structured schema generation with local fallback and quirk mitigation.
  7. **Background Queue Setup:** Evaluate and initialize Chancy (or Celery + Valkey) for asynchronous background tasks.
- **Verification:** Migration script round-trip verification; egress blocker unit tests verifying blocked outbound calls; Alembic upgrade/downgrade smoke tests.

---

### Phase 2: Real Amazon Connector & Seller Performance
- **Objective:** Integrate the official Amazon SP-API SDK for Amazon.in (`A21TJRUUN4KGV`) with zero web scraping.
- **Key Tasks:**
  1. **SP-API SDK Integration:** Integrate `amzn-sp-api` pointing to EU endpoint (`sellingpartnerapi-eu.amazon.com`).
  2. **Token Management:** Implement LWA OAuth token refresh with secure caching and backoff.
  3. **Reports API Ingestion:** Implement ingestion and parsing for:
     * `GET_SALES_AND_TRAFFIC_REPORT`
     * `GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA`
  4. **Listings & Inventory Endpoints:** Connect real catalog queries with schema validation.
  5. **Capability Matrix & CSV Fallback:** Implement seamless fallback to CSV data providers when live credentials are unconfigured.
- **Verification:** Mock SP-API test suite verifying report deserialization; rate-limit backoff verification; CSV fallback equivalence checks.

---

### Phase 3: Competitor Intelligence & Constrained Pricing
- **Objective:** Build the cost-complete Decimal pricing engine and prospective competitor snapshotting.
- **Key Tasks:**
  1. **SP-API Competitive Summary Batching:** Ingest `getCompetitiveSummary` (up to 20 ASINs per call) for Buy Box and competitor prices.
  2. **Prospective Snapshot Storage:** Store time-series competitor price and rank observations in PostgreSQL.
  3. **3-Tier Matching Implementation:** Categorize observations into Tier 1 (Same ASIN), Tier 2 (Exact Equivalent), Tier 3 (Substitute).
  4. **High-Precision Decimal Pricing Engine:** Implement `pricing_engine` with `decimal.Decimal` arithmetic for contribution margin, breakeven, and target margin.
  5. **Margin Floor & DO_NOT_MATCH Enforcement:** Enforce inviolable lower bounds and confidence downgrades on >15% price dispersion.
  6. **Volume Scenarios:** Implement what-if margin modeling at current volume.
- **Verification:** Pytest test suite covering decimal precision, fee tier thresholds, unreachable target margin safety, and DO_NOT_MATCH rules.

---

### Phase 4: Market Radar, Brand Analytics & Opportunities
- **Objective:** Implement free public intelligence and search term analytics.
- **Key Tasks:**
  1. **GDELT 2.0 Doc API Ingestion:** Query global news for supply chain, tariff, and category signals without API keys.
  2. **Public RSS Feed Engine:** Parse trade and regulatory news feeds via `feedparser`.
  3. **Google Trends CSV Parser:** Ingest public macro trend files.
  4. **Brand Analytics Search Terms:** Ingest search frequency rank and top clicked ASIN shares.
  5. **Unified Opportunity & Attention Scoring:** Expand `opportunity_engine` into full 0–100 itemized Attention Score.
  6. **Structured Intelligence Briefs:** Produce auditable Markdown briefs citing verbatim evidence.
- **Verification:** Unit tests verifying GDELT JSON parsing, RSS feed deduplication, and Opportunity Score calculation bounds.

---

### Phase 5: Forecasting & Durable Automation
- **Objective:** Deploy advanced statistical time-series forecasting and safe automation rules.
- **Key Tasks:**
  1. **StatsForecast Integration:** Integrate Nixtla's `statsforecast` (AutoARIMA, Croston, SBA, Naive, HistoricAverage).
  2. **Stockout-Censored Demand Adjustment:** Implement uncensoring algorithm to impute latent demand during zero-inventory days.
  3. **Dynamic Safety Stock & ROP:** Implement formulas accounting for demand and lead-time variance.
  4. **Durable Automations Engine:** Build rule evaluator (`IF condition THEN propose_action`) with human safety limits.
  5. **Action Center Queue:** Implement operator approval workflow (Approve, Reject with reason, Snooze 7 days).
- **Verification:** Forecast accuracy backtesting (MAE, RMSE, MAPE); uncensoring validation tests; automation trigger unit tests.

---

### Phase 6: Complete UI/UX Redesign ("The Seller Control Room")
- **Objective:** Execute full frontend redesign across all 11 core routes per `DESIGN.md`.
- **Key Tasks:**
  1. **Design Tokens & Palette:** Implement light-first default palette with forest/sage accents (`#1B4332`, `#2D6A4F`, `#52B788`, `#D8F3DC`).
  2. **Core Layout:** Build persistent Sidebar, Topbar with Provenance Legend and System Health, and command palette.
  3. **Implement the 11 Unified Routes:**
     * Overview (`/overview`)
     * Product Portfolio (`/portfolio`)
     * Product Workspace (`/products/:id` with 7 Tabs)
     * Competitor Watch (`/competitors`)
     * Market Radar (`/market-radar`)
     * Product Opportunities (`/opportunities`)
     * Pricing Lab (`/pricing-lab`)
     * Action Center (`/actions`)
     * Automations (`/automations`)
     * Research Reports (`/reports`)
     * Data Connections & Settings (`/settings`)
  4. **Provenance Badging:** Render standardized badges across every data table, metric card, and chart.
  5. **Responsive Layouts:** Verify flawless rendering at 1440px desktop, 1024px tablet, and 390px mobile viewports.
- **Verification:** `npm run build` cleanly; `oxlint` 0 errors; browser click-through across all 11 routes; mobile viewport overflow test (`scrollWidth === clientWidth`).

---

### Phase 7: Security, Hardening & Verification
- **Objective:** Perform end-to-end hardening, credential encryption, and comprehensive verification.
- **Key Tasks:**
  1. **Credential Encryption at Rest:** Implement AES-256 Fernet encryption for stored SP-API credentials.
  2. **Network Security Audit:** Confirm zero egress leakage in `FREE_ONLY=true` mode.
  3. **Full Integration Test Suite:** Run end-to-end integration tests spanning backend, database, queue, and frontend API clients.
  4. **Performance Benchmarking:** Validate <50ms engine computations and <3s Ollama responses.
  5. **Documentation Finalization:** Update README, architecture records, and user guides.
- **Verification:** Complete automated test matrix pass; security audit checklist confirmed; final verification sign-off.

