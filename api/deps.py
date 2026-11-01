"""
deps.py — one place that puts agent/, signals/, db/, eval/, data/ on
sys.path so routers can import their flat top-level modules
(`import db`, `from research_agent import ...`, etc.) exactly the way
app.py used to. Import this before anything else, in main.py and in
every router module — the sys.path.insert calls are idempotent
(guarded by membership check) so importing it repeatedly is safe.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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

