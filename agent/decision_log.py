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

# Anchored to the project root (not the process CWD) so the log lands
# in the same place whether this is run from agent/, the project root
# (Streamlit, Phase 5), or anywhere else. A bare relative env value is
# resolved against the project root; an absolute one is used as-is.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_project_path(env_var: str, default_name: str) -> Path:
    raw = os.environ.get(env_var, default_name)
    path = Path(raw)
    return path if path.is_absolute() else _PROJECT_ROOT / path


LOG_PATH = _resolve_project_path("DECISION_LOG_PATH", "decisions.log.jsonl")


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


def read_decisions(
    limit: int | None = None,
    product_name: str | None = None,
    agent: str | None = None,
    action: str | None = None,
) -> list[dict]:
    """Read back the append-only trace, newest first. Pure read — never
    mutates LOG_PATH. Filters are exact-match (product_name is matched
    case-insensitively since it's free text passed by callers)."""
    if not LOG_PATH.exists():
        return []

    entries: list[dict] = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # A single corrupted line must never take down every
                # reader of the trace (activity feed, agent status,
                # product detail) — skip it and keep going.
                continue

    if product_name is not None:
        needle = product_name.strip().lower()
        entries = [e for e in entries if e.get("product_name", "").strip().lower() == needle]
    if agent is not None:
        entries = [e for e in entries if e.get("agent") == agent]
    if action is not None:
        entries = [e for e in entries if e.get("action") == action]

    entries.reverse()  # newest first
    if limit is not None:
        entries = entries[:limit]
    return entries
