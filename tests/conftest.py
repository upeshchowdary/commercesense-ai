import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("agent", "signals", "db", "eval", "data", "intelligence", "providers", "api", "."):
    p = str(ROOT / sub) if sub != "." else str(ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
