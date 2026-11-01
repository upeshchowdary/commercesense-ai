# CommerceSense AI v3 — Product Specification

> **Product Document:** `PRODUCT.md`  
> **Status:** Canonical Definition  
> **Version:** 3.0.0 (Free-First Master Specification)  
> **Art Direction:** The Seller Control Room  

---

## 1. Vision & Core Value Proposition

### 1.1 Product Vision
**CommerceSense AI v3** is the **Seller Control Room** for independent and brand sellers on Amazon. It is designed to replace fragmented spreadsheets, black-box agency fees, and expensive recurring SaaS subscriptions with an uncompromising, free-first, privacy-respecting intelligence and decision platform.

The core design principle is **Decision Support Over Autonomy**: CommerceSense AI is not an unchecked autonomous bot that changes listing titles or drops prices while the seller sleeps. It is a high-precision instrument that surfaces critical risks, performs rigorous financial arithmetic, presents auditable evidence, and queues justified recommendations for human confirmation.

### 1.2 The One-Sentence Outcome
> *"Flag which of my products need attention this week — stockout, wasted ad spend, falling rank, margin erosion, or market risk — and tell me why, with mathematically verified evidence, before it costs me money."*

---

## 2. Target User Personas

1. **Amazon.in & Global Brand Owners (Private Label Sellers)**
   - Need clear oversight of inventory runways, Buy Box defense, and brand perception.
   - Constrained by margins; cannot afford $500–$2,000/month tool stacks (Helium10, Keepa, JungleScout, Pacvue).
   - Require full compliance with Amazon Policies (strictly zero web scraping).

2. **Supply Chain & Inventory Managers**
   - Need reliable lead-time forecasting and safety-stock recommendations.
   - Suffer from stockout censorship (unobserved demand during out-of-stock periods skewing historical run-rates).
   - Value clear, deterministic replenishment math over probabilistic "black box" claims.

3. **Performance Marketing & Ad Ops Managers**
   - Need immediate detection of PPC budget bleeding (high spend, zero sales, or ROAS below target).
   - Require real-time alerts when ad spend continues on products that are losing the Buy Box or approaching stockout.

4. **Financial Controllers & Operators**
   - Demand contribution margin transparency: exact unit economics factoring in COGS, referral fees, FBA fulfillment fees, closing fees, and packaging costs.
   - Require strict margin floors that cannot be breached by automated or hasty repricing.

---

## 3. Strict Free-First & Compliance Policy

CommerceSense AI v3 operates under a strict, verifiable Free-First architecture:

```
+------------------------------------------------------------------------+
|                      STRICT FREE-FIRST POLICY                          |
|             FREE_ONLY = true  |  ALLOW_PAID_PROVIDERS = false          |
+------------------------------------------------------------------------+
| [PROHIBITED] Paid APIs & Hosted Services:                              |
|   x Tavily, SerpAPI, Perplexity API                                    |
|   x Keepa API, Sorftime, Helium10, Apify                               |
|   x OpenAI API, Anthropic Claude API, Hosted Gemini API                |
|                                                                        |
| [PERMITTED] Free, Local, & Official Infrastructure:                    |
|   ✓ Official Amazon SP-API SDK (amzn-sp-api) via EU Endpoint           |
|   ✓ Public News Intelligence: GDELT 2.0 Doc API (100% Free, No Key)    |
|   ✓ Public Syndication: RSS Feeds (Category, Regulatory, E-Commerce)   |
|   ✓ Public Macro Trends: Google Trends CSV Download / Heuristics       |
|   ✓ Local LLM: Ollama (http://localhost:11434) with JSON Schemas       |
|   ✓ 100% Deterministic Fallback when LLM is offline                    |
|   ✓ High-Performance Time-Series: StatsForecast (Nixtla)               |
|   ✓ Zero Amazon Scraping: Strict zero-HTML-scraping compliance        |
+------------------------------------------------------------------------+
```

### 3.1 Zero Amazon Scraping Compliance
- CommerceSense AI strictly complies with Amazon’s Developer Agreement and Acceptable Use Policy (AUP).
- **Under no circumstances does CommerceSense AI scrape Amazon HTML pages, bypass CAPTCHAs, or rotate consumer proxies.**
- All Amazon marketplace data is ingested strictly through:
  1. The official Selling Partner API (SP-API) using developer credentials.
  2. Direct seller data imports via standardized CSV files.

### 3.2 Optional Local AI with Deterministic Guarantee
- Every metric, score, margin, and recommendation is calculated deterministically in plain Python and SQL.
- Local LLM inference (via Ollama running `qwen3-vl:4b`, `llama3.2`, or `mistral`) is used exclusively for summarizing or phrasing explanations in plain English.
- If Ollama is unreachable, unconfigured, or fails to parse, the entire system functions without degradation: all deterministic insights, tables, and scores remain 100% operational with an honest `"ai_explanation.available: false"` flag.

---

## 4. Provenance & Trust Hierarchy

Every metric, chart, table cell, and insight across all 11 routes displays an explicit **Provenance Envelope** consisting of 8 standard classifications:

| Provenance Badge | Description | Visual Token | Source Type |
|:---|:---|:---:|:---|
| `AMAZON_OFFICIAL` | Ingested directly from official Amazon SP-API reports or endpoints | Forest Green Solid | Authoritative API |
| `PUBLIC_NEWS` | Retrieved from GDELT 2.0 Doc API or verified public RSS feeds | Deep Teal Outline | Public Data |
| `SELLER_INPUT` | Explicitly configured by seller (COGS, target margins, lead times, CSVs) | Slate Gray Solid | User Input |
| `CALCULATED` | Deterministic mathematical calculation executed locally in Python/SQL | Blue Accent Outline | Code Computation |
| `MODELLED` | Statistical forecast (StatsForecast) or local AI explanation (Ollama) | Purple Outline | Model/Algorithm |
| `CACHED` | Valid historical data retrieved from local cache within defined TTL | Amber Outline | Local Cache |
| `DEMO` | Synthetic demonstration data (used in offline or evaluation mode) | Cool Gray Dotted | Local Synthetic |
| `MISSING` | Required data unavailable; flagged honestly without fabrication | Crimson Muted | Unpopulated Data |

### Grounding Rules
1. **Verbatim Evidence Requirement:** No insight or recommendation may claim a market condition or review sentiment without citing verbatim source text stored in the system.
2. **Number Hallucination Prohibition:** AI title rewrites or diagnostic explanations are automatically rejected by code guardrails if they introduce any numeric value not present in the original input data.
3. **Audit Trail Immutability:** Every human decision, AI evaluation, and data import is logged to an append-only audit trace (`decisions.log.jsonl` / PostgreSQL audit log).

---

## 5. Core Feature Matrix — The 11 Unified Routes

CommerceSense AI v3 organizes the entire seller workflow into 11 purpose-built routes:

```
+---------------------------------------------------------------------------+
|                    THE 11 SELLER CONTROL ROOM ROUTES                      |
+----+-----------------------+----------------------------------------------+
| 01 | Overview              | Executive Control Room, attention leaderboard|
| 02 | Product Portfolio     | Master catalog inventory, health indicators  |
| 03 | Product Workspace     | 7 deep-dive tabs for individual ASIN/SKU     |
| 04 | Competitor Watch      | Prospective price tracking & Buy Box radar   |
| 05 | Market Radar          | GDELT news, RSS signals, search trends       |
| 06 | Product Opportunities | Algorithmic Attention Score & revenue unlock |
| 07 | Pricing Lab           | Interactive margin simulator & fee breakdown |
| 08 | Action Center         | Unified recommendation & approval queue      |
| 09 | Automations           | Durable rule definitions & execution logs    |
| 10 | Research Reports      | Auditable intelligence briefs & PDF export   |
| 11 | Data & Settings       | SP-API status, Ollama health, CSV pipelines  |
+----+-----------------------+----------------------------------------------+
```

### Route 01: Overview (`/overview`)
- **Purpose:** High-level executive situational awareness.
- **Key Modules:**
  - **KPI Metric Strip:** 30d Revenue, Blended Contribution Margin %, Total Attention Score, Stockout Risks Count, Ad Spend Waste at Risk ($).
  - **This Week's Attention Leaderboard:** Prioritized list of SKUs requiring operator review, ordered by calculated dollars at risk.
  - **Portfolio Risk Matrix:** 2D scatter / bubble chart plotting Margin % vs. Days of Cover.
  - **Recent Action Queue:** Quick-approval cards for top pending decisions.

### Route 02: Product Portfolio (`/portfolio`)
- **Purpose:** Full catalog operational table with multi-dimensional filtering.
- **Key Modules:**
  - Table columns: SKU, ASIN, Product Name, Category, Current Price, Contribution Margin %, Days of Cover, Rating, Attention Score, Provenance.
  - Quick Filters: `Stockout Risk`, `Below Margin Floor`, `Emerging Review Issue`, `PPC Waste`, `Listing Degraded`.
  - Batch Actions: Bulk export, Trigger intelligence audit, Batch reorder simulation.

### Route 03: Product Workspace (`/products/:id`)
- **Purpose:** Comprehensive operational command for a single SKU across 7 dedicated tabs:
  1. **Overview Tab:** SKU summary, 60-day historical chart (sales, inventory, Buy Box, rank), current Attention Score breakdown.
  2. **Listing Tab:** 0–100 Listing Health Score across 5 categories (completeness, quality, consistency, keyword hygiene, media), rule breakdown, optional Ollama title rewrite with grounding checks.
  3. **Pricing Tab:** Unit economics breakdown (COGS, referral fees, fulfillment, closing fees), breakeven and target margin prices, competitor price distribution, recommended price range, price simulator.
  4. **Reviews Tab:** 7/30/90-day review velocity, rating distribution, deterministic keyword themes with verbatim excerpts, emerging negative issue spike detection, local semantic clustering.
  5. **Inventory Tab:** Daily demand (7d/14d/30d weighted), days of cover, safety stock, reorder point, suggested reorder quantity, 60-day inventory burn chart with inbound shipment scenario.
  6. **Competitors Tab:** 3-tier competitor comparison table (Same ASIN, Exact Equivalent, Substitute), Buy Box share tracker, price spread contradiction warnings.
  7. **Forecast Tab:** StatsForecast demand projection (AutoARIMA, Croston, Naive), stockout-censored baseline comparison, confidence intervals (80%/95%).

### Route 04: Competitor Watch (`/competitors`)
- **Purpose:** Cross-catalog competitive intelligence and price monitoring.
- **Key Modules:**
  - Competitor price observation grid with 3-tier classification.
  - Prospective price/rank history snapshotting in PostgreSQL.
  - Contradiction and dispersion alerts (>15% price disagreement among sources).
  - Buy Box status alerts (identifying suppressions or third-party wins).

### Route 05: Market Radar (`/market-radar`)
- **Purpose:** Macro market intelligence powered strictly by free, public data.
- **Key Modules:**
  - **GDELT News Feed:** Real-time global trade, tariff, supply chain, and category news from the GDELT 2.0 Doc API.
  - **RSS Feed Digest:** Curated category and regulatory trade feeds parsed locally.
  - **Google Trends Signals:** Public trend momentum indicators.
  - Search term volume and click-share metrics (via Brand Analytics reports when SP-API is active).

### Route 06: Product Opportunities (`/opportunities`)
- **Purpose:** Systematic opportunity discovery and risk triage.
- **Key Modules:**
  - Algorithmic Attention Score ranking (0–100 itemized points).
  - Component breakdown: Inventory Risk (max 30), Review Risk (max 25), Listing Issues (max 20), Pricing Pressure (max 15), Active Signals (max 10).
  - Estimated Revenue Unlock ($ at risk that can be saved through timely intervention).

### Route 07: Pricing Lab (`/pricing-lab`)
- **Purpose:** Standalone financial modeling and pricing sensitivity simulator.
- **Key Modules:**
  - Interactive price slider testing margin implications across volume scenarios.
  - Cost structure editor (COGS, referral fees, packaging, ad spend allocation).
  - Fee sensitivity curve plotting Amazon referral and closing fee tiers.
  - Margin Floor enforcement preview: visually blocking recommendations below target viability.

### Route 08: Action Center (`/actions`)
- **Purpose:** Centralized operator inbox for all system-generated recommendations.
- **Key Modules:**
  - Recommendation cards with structured "Why Panel":
    * *What happened?*
    * *Why does it matter?*
    * *Evidence & Calculation*
    * *What if nothing is done?*
    * *Recommended Action*
    * *Why not? Alternatives considered*
  - Operator actions: **Approve**, **Reject** (with required reason), **Snooze (7 Days)**, **Request More Data**.
  - All actions append directly to the immutable decision log.

### Route 09: Automations (`/automations`)
- **Purpose:** Durable rule definitions with human safety boundaries.
- **Key Modules:**
  - Rule Builder: `IF [metric] [operator] [threshold] THEN [propose_action]`.
  - Guardrails: Maximum allowable price movement (e.g. ±5%), maximum reorder capital, required human sign-off toggles.
  - Automation Execution Log: Historical record of rules evaluated and triggered.

### Route 10: Research Reports (`/reports`)
- **Purpose:** Archival intelligence reports and client/executive deliverables.
- **Key Modules:**
  - Weekly Executive Briefing generator.
  - Export capabilities: Structured Markdown download and print-ready CSS PDF generation.
  - Verbatim citation index for all included claims.

### Route 11: Data Connections & Settings (`/settings`)
- **Purpose:** Technical connections, provider configuration, and diagnostics.
- **Key Modules:**
  - **Amazon SP-API Connection:** LWA Client credentials, refresh token status, EU endpoint health check (`sellingpartnerapi-eu.amazon.com`).
  - **Local Ollama Integration:** Base URL (`http://localhost:11434`), detected models (`qwen3-vl`, `llama3.2`), reachability latency.
  - **Free-First Policy Status:** Indicator showing `FREE_ONLY=true` and egress filters active.
  - **CSV Data Ingestion Hub:** Template download, file upload, validation preview, and commit workflow for Listing, Pricing, Reviews, Inventory, and Competitor datasets.
  - **Database Migration & Diagnostics:** Schema version, Alembic migration state, row counts, cache eviction tools.

---

## 6. Success Metrics & Non-Functional Requirements

1. **Deterministic Speed:** Core rule evaluations, inventory models, and price calculations must complete in **< 50 milliseconds** per product.
2. **Local LLM Performance:** Ollama explanations must stream or return within **< 3 seconds** on standard local hardware (4-8GB VRAM or modern CPU).
3. **Zero Data Corruption:** Financial calculations must utilize decimal precision (`Decimal`), eliminating floating-point rounding errors.
4. **Air-Gapped Compatibility:** The entire system must run completely offline in DEMO or CSV mode without an active internet connection.
5. **High Data Density UI:** Interfaces must present comprehensive tabular data and charts at standard 1440px resolution without artificial spacing or oversized cards.

