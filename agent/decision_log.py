"""
decision_log.py  the single append-only trace file for every agent
decision in the system. Used by the two live agents AND the fake-data
signal detectors, so there is exactly one place to look for "who
decided what, on what evidence, and when" (CUBE face 5).

One JSON line per event. Never mutated, never deleted.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(os.environ.get("DECISION_LOG_PATH", "decisions.log.jsonl"))


def log_decision(
    agent: str,
    product_name: str,
    action: str,
    detail: dict | None = None,
) -> None:
    """Append one decision-trace entry. Deliberately does not swallow
    write failures  if logging breaks, you want to know immediately,
    not silently lose your trace."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "product_name": product_name,
        "action": action,
        "detail": detail or {},
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
