# sydon-1  Amazon Seller Copilot

Practice project for the CUBE Buildathon (Sydon AI / CodeQuesters, 2026).

One-sentence outcome: "Flag which of my products need attention this week  stockout, wasted ad spend, falling rank, or policy/market risk  and tell me why, before it costs me money."

## Project structure

- `agent/`  Shared contracts, decision logging, cache, and live-agent modules.
- `data/`  Synthetic seller-account data generation (signals + the four intelligence modules).
- `db/`  Database schema and access layer (`db.py` for the original entities, `intelligence_db.py` for the four modules).
- `signals/`  Deterministic inventory, PPC waste, and rank/Buy Box signals.
- `intelligence/`  Deterministic engines for Listing, Pricing, Review, and Inventory Intelligence, plus the Commerce Opportunity Engine.
- `providers/`  Pluggable LLM (Ollama/Gemini), web-search, and Amazon-data provider abstractions used by the intelligence modules.
- `eval/`  Labeled evaluation data and evaluation scripts.
- `api/`  FastAPI layer exposing the above over HTTP for the frontend. Thin wrappers only  no agent/signal/engine logic lives here.
- `frontend/`  React + TypeScript + Vite SPA (the UI).
- `tests/`  pytest unit tests for the deterministic engines and grounding guardrails.

The synthetic side uses locally generated fake seller data. The live side uses Tavily for web search and Gemini (or a local Ollama model) for grounded insight generation. These sides remain clearly separated.

## Intelligence modules

Four additional modules extend the original signal detection, following the
same "deterministic logic first, LLM second" philosophy: every number shown
(score, margin, days of cover, rating stats) is computed in plain Python, and
the LLM is only ever used afterward to explain an already-verified result in
plain English  never to produce the number itself.

- **Listing Intelligence**  a rule engine scores title/bullets/description/
  attributes/images completeness and quality (0100, "CommerceSense Listing
  Health Score", never claimed as an official Amazon metric), with an
  optional AI-proposed title rewrite that's rejected if it introduces any
  number not present in the original listing data.
- **Pricing Intelligence**  contribution margin, breakeven price, and a
  target-margin price computed from cost inputs (COGS, fees, target margin);
  a price-state classification and a justified recommended range, plus a
  what-if price simulator. Competitor price observations are demo/CSV data by
  default, or optionally live (reusing the existing Research Agent, never a
  second research engine).
- **Review Intelligence**  rating distribution, review velocity (7/30/90-day
  windows), and deterministic theme/keyword frequency with real review
  excerpts as evidence; emerging-issue detection compares a recent window
  against the prior one and requires a real, sustained spike before flagging
  anything.
- **Inventory Intelligence**  reuses the existing `daily_metrics` history
  (no new inventory data invented): weighted demand, days of cover, reorder
  point, safety stock, a suggested reorder quantity, and a scenario
  simulator/forecast, all clearly labeled as projections, not facts.

A fifth endpoint, `GET /api/products/{id}/intelligence`, synthesizes all four
plus the existing synthetic signals into one per-product, fully-itemized
**Attention Score**  see it live at `/products/:id/intelligence` in the
frontend, the single best page for a quick demo. The same four module tabs
also appear inline on the regular Product Detail page, and the Products/
Overview pages show a condensed per-product health-badge row and an
"Attention" leaderboard so a judge never has to click into every product to
see what needs attention.

Every recommendation carries a collapsible **"Why does this matter?"** panel
(what happened, why it matters, evidence, the calculation, what happens if
nothing is done, the proposed action, what's missing) and, for pricing and
inventory, a **"Why not? Alternatives considered"** panel  this is decision
support, never an autonomous "just do it" claim.

Products can be filtered with `listing:needs-attention`, `pricing:below-margin`,
`reviews:emerging`, and `inventory:stockout-risk` typed directly into the
Products page search box (client-side, no dedicated search API), and the
command palette (`Ctrl/Cmd+K`) has a "Run Full Intelligence  {product}" entry
per product alongside the existing page/product/signal jumps.

Pricing's recommended range also does real **contradiction handling** (spec
§20): if competitor price observations disagree with each other by more than
15% of the median, the recommendation's confidence is downgraded to `low` and
the reasoning says so explicitly, instead of silently trusting a median built
from disagreeing sources.

### Feature flags

`ENABLE_LISTING_INTELLIGENCE` / `ENABLE_PRICING_INTELLIGENCE` /
`ENABLE_REVIEW_INTELLIGENCE` / `ENABLE_INVENTORY_INTELLIGENCE` (all default
`true`) actually gate each module's router at startup in `api/main.py`  set
one to `false` and that module's endpoints 404 rather than just being hidden
in the UI. `GET /api/health` reports the live state of every flag (booleans
only, never secrets).

### Providers  all free, all optional

- **LLM**: `LLM_PROVIDER=ollama` (default, free, local  point `OLLAMA_BASE_URL`
  at a running Ollama instance) or `gemini` (reuses `GEMINI_API_KEY`). If
  neither is reachable, every module still returns its full deterministic
  analysis with `ai_explanation.available: false` and a clear message 
  never a crash, never a fabricated explanation.
- **Web search**: `providers/websearch.py` defines a `WebSearchProvider`
  interface with two implementations  `TavilyProvider` (default, wraps the
  existing Research Agent, no second research engine) and `SearXNGProvider`
  (a real HTTP client against a self-hosted SearXNG instance's JSON API,
  used only when `ENABLE_SEARXNG=true` and `SEARXNG_URL` point at one; falls
  back to Tavily automatically otherwise  this project does not host a
  SearXNG instance itself).
- **Review theme clustering**: `intelligence/review_engine.py`'s deterministic
  keyword/phrase theme detection (the only thing anything else depends on)
  is optionally supplemented by `semantic_theme_clusters()`  local
  sentence-transformers embeddings + scikit-learn KMeans, purely an extra
  lens shown alongside the deterministic themes. Degrades to an empty list
  (not an error) if those packages aren't installed or there isn't enough
  review text to cluster.
- **Amazon data**: `DemoDataProvider` (the synthetic dataset, default) and
  `CSVDataProvider` (see below) are fully implemented. `SPAPIProvider` is a
  documented interface stub only  there's no way to test a real SP-API
  integration without live seller credentials, so it reports itself
  unconfigured rather than pretending to work. The whole app runs fully
  without any Amazon credentials.

### CSV import

No Amazon API needed to get real data in: `GET /api/data-import/template/
{listing|pricing|reviews|inventory}` returns a starter CSV, and `POST /api/
data-import/{type}/validate` (then `/commit`) validates every row and reports
exactly which rows failed and why  nothing is silently dropped.

## Running it

Backend (from the project root, with `.venv` activated and `.env` populated):

```
uvicorn api.main:app --reload --port 8000
```

Frontend (from `frontend/`, separate terminal):

```
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`, so the backend must be running first.
