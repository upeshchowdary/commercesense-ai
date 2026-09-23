# sydon-1  Amazon Seller Copilot

Practice project for the CUBE Buildathon (Sydon AI / CodeQuesters, 2026).

One-sentence outcome: "Flag which of my products need attention this week  stockout, wasted ad spend, falling rank, or policy/market risk  and tell me why, before it costs me money."

## Project structure

- `agent/`  Shared contracts, decision logging, cache, and live-agent modules.
- `data/`  Synthetic seller-account data generation.
- `db/`  Synthetic data database schema and access layer.
- `signals/`  Deterministic inventory, PPC waste, and rank/Buy Box signals.
- `eval/`  Labeled evaluation data and evaluation scripts.
- `api/`  FastAPI layer exposing the above over HTTP for the frontend. Thin wrappers only  no agent/signal logic lives here.
- `frontend/`  React + TypeScript + Vite SPA (the UI).

The synthetic side uses locally generated fake seller data. The live side uses Tavily for web search and Gemini for grounded insight generation. These sides remain clearly separated.

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
