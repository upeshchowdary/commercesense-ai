"""
deps.py — one place that puts agent/, signals/, db/, eval/, data/ on
sys.path so routers can import their flat top-level modules
(`import db`, `from research_agent import ...`, etc.) exactly the way
app.py used to. Import this before anything else, in main.py and in
every router module — the sys.path.insert calls are idempotent
(guarded by membership check) so importing it repeatedly is safe.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Serverless hosts (Vercel sets VERCEL=1 at runtime) mount the deployed
# code read-only; only /tmp is writable. Every writer in this project
# (synthetic SQLite DB, research cache, decision log, credential vault)
# already resolves its path from an env var, so redirect them here —
# this module is imported before any of them read that env var.
# setdefault: an explicitly configured path always wins.
SERVERLESS_TMP = Path("/tmp/seller-copilot")


def is_serverless() -> bool:
    return bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


if is_serverless():
    SERVERLESS_TMP.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SQLITE_DB_PATH", str(SERVERLESS_TMP / "amazon_copilot.db"))
    os.environ.setdefault("CACHE_DB_PATH", str(SERVERLESS_TMP / "research_cache.db"))
    os.environ.setdefault("DECISION_LOG_PATH", str(SERVERLESS_TMP / "decisions.log.jsonl"))
    os.environ.setdefault("VAULT_DIR", str(SERVERLESS_TMP / ".vault"))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
else:
    # Ensure PROJECT_ROOT is at index 0
    sys.path.remove(str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT))

for _sub in ("agent", "signals", "db", "eval", "data", "intelligence", "providers", "tasks"):
    _p = str(PROJECT_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

