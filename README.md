# sydon-1  Amazon Seller Copilot

Practice project for the CUBE Buildathon (Sydon AI / CodeQuesters, 2026).

One-sentence outcome: "Flag which of my products need attention this week  stockout, wasted ad spend, falling rank, or policy/market risk  and tell me why, before it costs me money."

## Project structure

- `agent/`  Shared contracts, decision logging, cache, and live-agent modules.
- `data/`  Synthetic seller-account data generation.
- `db/`  Synthetic data database schema and access layer.
- `signals/`  Deterministic inventory, PPC waste, and rank/Buy Box signals.
- `eval/`  Labeled evaluation data and evaluation scripts.
- `app.py`  Streamlit application entry point.

The synthetic side uses locally generated fake seller data. The live side uses Tavily for web search and Gemini for grounded insight generation. These sides remain clearly separated.
