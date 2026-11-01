# CommerceSense AI v3 — Data Sources & Provenance Specification

> **Data Specification Document:** `docs/DATA_SOURCES.md`  
> **Status:** Canonical Specification  
> **Target Version:** CommerceSense AI v3  

---

## 1. The Provenance Classification Framework

In CommerceSense AI v3, **no data point exists without an explicit provenance envelope**. Operators must be able to glance at any metric, chart, or recommendation and immediately know whether it originated from an official Amazon API, a public news feed, a seller-configured spreadsheet, a deterministic formula, or an algorithmic model.

Every field and metric returned across the API and displayed in the UI is classified into one of eight standardized provenance envelopes:

```
+==================================================================================================+
|                                  THE 8 PROVENANCE ENVELOPES                                      |
+===================+===================================================+==========================+
| ENVELOPE          | DEFINITION                                        | PRIMARY SOURCES          |
+===================+===================================================+==========================+
| AMAZON_OFFICIAL   | Authoritative data ingested directly from Amazon  | SP-API Reports, Pricing  |
|                   | Selling Partner API without alteration.           | & Listings Endpoints     |
+-------------------+---------------------------------------------------+--------------------------+
| PUBLIC_NEWS       | Unrestricted, free public domain information      | GDELT 2.0 Doc API,       |
|                   | retrieved via official HTTP REST or RSS feeds.    | Category RSS Feeds       |
+-------------------+---------------------------------------------------+--------------------------+
| SELLER_INPUT      | Private business configuration parameters provided| Seller CSV Uploads,      |
|                   | directly by the account operator.                 | Settings UI Forms        |
+-------------------+---------------------------------------------------+--------------------------+
| CALCULATED        | Deterministic financial arithmetic or rule-based  | Python Pricing, Inventory|
|                   | logic computed locally in code without an AI model| and Listing Rule Engines |
+-------------------+---------------------------------------------------+--------------------------+
| MODELLED          | Statistical forecasts, machine learning outputs,  | StatsForecast Models,    |
|                   | or qualitative local LLM explanations.            | Local Ollama Adapter     |
+-------------------+---------------------------------------------------+--------------------------+
| CACHED            | Valid historical data retrieved from local store  | SQLite/Redis Cache       |
|                   | within defined TTL thresholds.                    | with timestamp           |
+-------------------+---------------------------------------------------+--------------------------+
| DEMO              | Deterministically seeded synthetic test data used | Seeded Synthetic Data    |
|                   | when running in local demonstration mode.         | (SEED=42)                |
+-------------------+---------------------------------------------------+--------------------------+
| MISSING           | Explicit indicator that a required data point     | Null/Empty Field with    |
|                   | is unpopulated; never fabricated or guessed.      | "Insufficient Data" tag  |
+===================+===================================================+==========================+
```

---

## 2. Exhaustive Metric & Field Provenance Mapping

The following tables specify the exact provenance classification for every field stored in the database, returned by API routes, and displayed on UI surfaces:

### 2.1 Product Catalog Master (`products`)
| Field Name | Storage Data Type | Provenance Envelope | Description & Source |
|:---|:---|:---:|:---|
| `product_id` | `VARCHAR(64)` PRIMARY KEY | `SELLER_INPUT` / `AMAZON_OFFICIAL` | Internal SKU identifier or Amazon Seller SKU |
| `asin` | `VARCHAR(10)` | `AMAZON_OFFICIAL` | Amazon Standard Identification Number |
| `name` | `VARCHAR(255)` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Canonical product title |
| `category` | `VARCHAR(64)` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Amazon Browse Node or catalog category |
| `base_price` | `DECIMAL(10, 2)` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Standard selling price in local currency |
| `currency` | `VARCHAR(3)` | `AMAZON_OFFICIAL` | Currency code (`INR` for Amazon.in, `USD` global) |

### 2.2 Daily Time-Series Metrics (`daily_metrics`)
| Field Name | Storage Data Type | Provenance Envelope | Description & Source |
|:---|:---|:---:|:---|
| `date` | `DATE` | `AMAZON_OFFICIAL` / `DEMO` | Activity date (ISO-8601 `YYYY-MM-DD`) |
| `units_sold` | `INTEGER` | `AMAZON_OFFICIAL` / `DEMO` | Units ordered from `GET_SALES_AND_TRAFFIC_REPORT` |
| `inventory_level` | `INTEGER` | `AMAZON_OFFICIAL` / `DEMO` | FBA fulfillable quantity from Inventory Summaries |
| `rank` | `INTEGER` | `AMAZON_OFFICIAL` / `DEMO` | Best Sellers Rank (BSR) in primary category |
| `has_buy_box` | `BOOLEAN` | `AMAZON_OFFICIAL` / `DEMO` | 1 if seller owned Buy Box; 0 otherwise |
| `ad_spend` | `DECIMAL(10, 2)` | `AMAZON_OFFICIAL` / `DEMO` | Sponsored Products PPC advertising spend |
| `ad_clicks` | `INTEGER` | `AMAZON_OFFICIAL` / `DEMO` | Total ad clicks registered on date |
| `ad_sales` | `DECIMAL(10, 2)` | `AMAZON_OFFICIAL` / `DEMO` | Attributed 7-day ad sales revenue |

### 2.3 Unit Economics & Cost Structure (`pricing_data`)
| Field Name | Storage Data Type | Provenance Envelope | Description & Source |
|:---|:---|:---:|:---|
| `cogs` | `DECIMAL(10, 2)` | `SELLER_INPUT` | Cost of Goods Sold per unit (from CSV/UI) |
| `referral_fee_pct` | `DECIMAL(6, 4)` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Amazon category referral fee rate (e.g. 0.1500) |
| `fulfillment_fee` | `DECIMAL(10, 2)` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | FBA pick & pack or Easy Ship fee per unit |
| `closing_fee` | `DECIMAL(10, 2)` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Amazon fixed closing fee based on price band |
| `other_cost` | `DECIMAL(10, 2)` | `SELLER_INPUT` | Packaging, inward freight, label costs |
| `target_margin_pct`| `DECIMAL(6, 4)` | `SELLER_INPUT` | Desired minimum contribution margin (e.g. 0.2000) |

### 2.4 Pricing Engine Outputs & Analyses (`pricing_analyses`)
| Metric Name | Return Type | Provenance Envelope | Calculation & Derivation |
|:---|:---|:---:|:---|
| `variable_cost` | `DECIMAL(10, 2)` | `CALCULATED` | `COGS + Referral_Fee + Fulfillment_Fee + Closing + Other` |
| `contribution` | `DECIMAL(10, 2)` | `CALCULATED` | `Current_Price - variable_cost` |
| `margin_pct` | `DECIMAL(6, 4)` | `CALCULATED` | `contribution / Current_Price` |
| `breakeven_price` | `DECIMAL(10, 2)` | `CALCULATED` | Price where `contribution == 0` |
| `target_margin_price` | `DECIMAL(10, 2)` | `CALCULATED` | Price achieving `target_margin_pct` |
| `price_state` | `ENUM` | `CALCULATED` | `BELOW_MARGIN_FLOOR`, `HEALTHY_RANGE`, `ABOVE_COMPETITIVE_RANGE`, `COMPETITIVE_PRESSURE` |
| `recommended_low` | `DECIMAL(10, 2)` | `CALCULATED` | Lower bound of recommended pricing window (guarded by margin floor) |
| `recommended_high`| `DECIMAL(10, 2)` | `CALCULATED` | Upper bound of recommended pricing window |
| `ai_explanation` | `JSON Object` | `MODELLED` | Plain-English summary from local Ollama (or fallback) |

### 2.5 Competitor Intelligence (`competitor_observations`)
| Field Name | Storage Data Type | Provenance Envelope | Description & Source |
|:---|:---|:---:|:---|
| `competitor_name`| `VARCHAR(128)` | `AMAZON_OFFICIAL` / `DEMO` | Competitor seller or brand name |
| `competitor_asin`| `VARCHAR(10)` | `AMAZON_OFFICIAL` / `DEMO` | Competitor ASIN |
| `observed_price` | `DECIMAL(10, 2)` | `AMAZON_OFFICIAL` / `DEMO` | Observed offer price from `getCompetitiveSummary` |
| `match_tier` | `ENUM` | `SELLER_INPUT` / `CALCULATED` | `TIER_1_SAME_ASIN`, `TIER_2_EQUIVALENT`, `TIER_3_SUBSTITUTE` |
| `observed_at` | `TIMESTAMP WITH TZ` | `AMAZON_OFFICIAL` / `DEMO` | Timestamp of price snapshot |
| `confidence` | `ENUM` | `CALCULATED` | Confidence rating (`high`, `medium`, `low` downgraded on >15% spread) |

### 2.6 Listing Intelligence (`listing_data` & `listing_audits`)
| Metric / Field | Return Type | Provenance Envelope | Description & Derivation |
|:---|:---|:---:|:---|
| `title` | `TEXT` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Current listing title on Amazon |
| `bullets` | `JSON ARRAY` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Key product feature bullet points |
| `image_count` | `INTEGER` | `AMAZON_OFFICIAL` / `SELLER_INPUT` | Number of active listing images |
| `listing_score` | `INTEGER (0-100)` | `CALCULATED` | Weighted score across completeness, quality, consistency, hygiene, media |
| `failed_rules` | `JSON ARRAY` | `CALCULATED` | Deterministic rules violated (e.g., repeated words, caps ratio, length) |
| `proposed_title` | `TEXT` | `MODELLED` | Title rewrite generated by local Ollama model |
| `grounding.grounded`| `BOOLEAN` | `CALCULATED` | Verification that proposed title contains NO new/fabricated numbers |

### 2.7 Review Intelligence (`review_items` & `review_analyses`)
| Metric / Field | Return Type | Provenance Envelope | Description & Derivation |
|:---|:---|:---:|:---|
| `avg_rating` | `DECIMAL(3, 2)` | `CALCULATED` | Arithmetic mean of customer star ratings |
| `negative_pct` | `DECIMAL(5, 2)` | `CALCULATED` | Percentage of 1-star and 2-star reviews |
| `velocity_30d` | `INTEGER` | `CALCULATED` | Total reviews received in the past 30 days |
| `themes` | `JSON ARRAY` | `CALCULATED` | Keyword/phrase frequency matching curated category vocabularies |
| `theme_evidence` | `JSON ARRAY` | `AMAZON_OFFICIAL` / `DEMO` | Verbatim review quotes evidencing flagged themes |
| `emerging_issues`| `JSON ARRAY` | `CALCULATED` | Themes demonstrating statistically significant spikes (>2.0x velocity) |
| `semantic_clusters`| `JSON ARRAY` | `MODELLED` | Sentence-transformers KMeans cluster centroids (optional local lens) |

### 2.8 Inventory Intelligence & Forecasting (`inventory_config` & `forecasts`)
| Metric / Field | Return Type | Provenance Envelope | Description & Derivation |
|:---|:---|:---:|:---|
| `current_inventory`| `INTEGER` | `AMAZON_OFFICIAL` / `DEMO` | Current fulfillable stock in FBA warehouses |
| `weighted_demand`| `DECIMAL(8, 2)` | `CALCULATED` | Recent 7d (3x), 14d (2x), and older (1x) weighted daily unit sales |
| `days_of_cover` | `DECIMAL(6, 1)` | `CALCULATED` | `current_inventory / weighted_demand` |
| `safety_stock` | `DECIMAL(8, 1)` | `CALCULATED` | Buffer units based on lead time and service level $Z$ |
| `reorder_point` | `DECIMAL(8, 1)` | `CALCULATED` | `(weighted_demand * lead_time) + safety_stock` |
| `suggested_reorder`| `INTEGER` | `CALCULATED` | Quantity needed to reach target stock, honoring MOQ and batch multiples |
| `forecast_series`| `JSON ARRAY` | `MODELLED` | StatsForecast time-series demand trajectory (AutoARIMA, Croston) |
| `uncensored_demand`| `JSON ARRAY` | `CALCULATED` | Historical sales imputed during zero-stock periods to eliminate bias |

### 2.9 Unified Commerce Attention Score (`opportunity_engine`)
| Metric Name | Return Type | Provenance Envelope | Calculation & Derivation |
|:---|:---|:---:|:---|
| `attention_score`| `INTEGER (0-100)` | `CALCULATED` | Unified sum of 5 itemized components: |
| • `inventory_risk`| `INTEGER (0-30)` | `CALCULATED` | 30 for Stockout Risk, 20 for Low Cover, 10 for Slow Moving |
| • `review_risk` | `INTEGER (0-25)` | `CALCULATED` | Based on negative % (>30% = 15pts) and emerging issue spike (10pts) |
| • `listing_issues`| `INTEGER (0-20)` | `CALCULATED` | Delineated by listing score bands (<40 = 20pts, <60 = 14pts, <80 = 8pts) |
| • `pricing_pressure`| `INTEGER (0-15)` | `CALCULATED` | 15 for Below Margin Floor, 8 for Above Range, 6 for Comp Pressure |
| • `existing_signals`| `INTEGER (0-10)` | `CALCULATED` | 6 points per high signal, 3 per medium signal (capped at 10) |

---

## 3. External Integration Contracts

### 3.1 Amazon Selling Partner API (SP-API)
- **Official Host:** `https://sellingpartnerapi-eu.amazon.com`
- **Default Marketplace ID:** `A21TJRUUN4KGV` (Amazon India - Amazon.in)
- **OAuth Protocol:** Login with Amazon (LWA) token endpoint (`https://api.amazon.com/auth/o2/token`).
- **Reports Consumed:**
  * `GET_SALES_AND_TRAFFIC_REPORT`: Daily ordered units, sales revenue, page views, Buy Box percentage.
  * `GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA`: Real-time warehouse fulfillable, unfulfillable, and inbound units.
  * `GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT`: Top search queries, search frequency rank, top 3 clicked ASINs with click/conversion share.
- **REST Endpoints Consumed:**
  * `getCompetitiveSummary` (`/products/pricing/v0/competitivePrice`): Real-time Buy Box and competitive pricing offers.
  * `getListingsItem` (`/listings/2021-08-01/items/{sellerId}/{sku}`): Complete catalog listing data.

### 3.2 GDELT 2.0 Doc API (Global Database of Events, Language, and Tone)
- **Protocol:** Public HTTP GET (No API Key Required).
- **Endpoint:** `https://api.gdeltproject.org/api/v2/doc/doc`
- **Query Parameters:**
  * `query`: Boolean search strings (e.g. `(amazon OR "e-commerce" OR supply chain) AND (tariff OR shortage OR logistics)`).
  * `mode`: `ArtList` (Article List).
  * `maxrecords`: `25`
  * `format`: `json`
  * `sort`: `DateDesc`
- **Extracted Fields:** Title, URL, Domain, Publication Date, Tone Score (Sentiment).

### 3.3 Public RSS News Syndication
- **Protocol:** HTTP GET via Python `feedparser` / `httpx`.
- **Target Feeds:**
  * Google News E-Commerce & Retail Feed.
  * Category-specific trade feeds (e.g. Consumer Electronics, Kitchenware, Personal Care).
- **Processing:** Stripping raw HTML/CDATA, hashing GUIDs for deduplication, extracting publication timestamps.

### 3.4 Local Ollama LLM Service
- **Protocol:** Local HTTP REST (`http://localhost:11434/api/generate`).
- **Target Models:** `qwen3-vl:4b` (default for combined multimodal/reasoning), `llama3.2:3b`, `mistral:7b`.
- **Constraint Enforcement:** `format: <json_schema>` matching Pydantic response models.
- **Fallback Rule:** Network timeout set to 15.0 seconds. On error or timeout, return `available: false` with deterministic fallback.

---

## 4. Blacklisted & Prohibited Services

In accordance with the **Strict Free-First Policy (`FREE_ONLY=true`)**, the following endpoints are hard-blocked by application middleware:

```
[EGRESS BLACKLIST]
x *.tavily.com          (Paid search API)
x *.serpapi.com         (Paid search scraping API)
x *.keepa.com           (Paid Amazon data API)
x *.sorftime.com        (Paid Amazon intelligence API)
x *.apify.com           (Paid web scraping platform)
x *.openai.com          (Hosted proprietary LLM)
x *.anthropic.com       (Hosted proprietary LLM)
x generativelanguage.googleapis.com (Hosted Gemini API in FREE_ONLY mode)
```

