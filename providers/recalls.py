"""
recalls.py — product-safety recall lookup against the US Consumer Product
Safety Commission (CPSC) public Recall Retrieval API. Free, official, and
needs NO API key.

    GET https://www.saferproducts.gov/RestWebServices/Recall?format=json&ProductName=<term>

Why it exists: the Insight Agent's "risk" category had nothing authoritative
to cite. A recall record is a real, dated, linkable government source.

Grounding rules (same spirit as the rest of the project):
  - This is a NAME match against CPSC's database, so every hit is reported
    as a *possible* match with its CPSC link -- never as "your product is
    recalled". The wording in `disclaimer` says so, and the UI shows it.
  - Every field returned is copied verbatim from CPSC's record (title, URL,
    date, hazards, remedies). Nothing is summarised or invented here.
  - If CPSC is unreachable, the result is `available: False` with the error.
    An empty list means "CPSC returned nothing", never "we could not check".
  - US-only: CPSC covers products sold in the United States.

Verified against CPSC's own documentation page: base URL, `format=json`,
and the `ProductName` / `Title` / `RecallDescription` query parameters, and
the JSON field names (RecallID, RecallNumber, RecallDate, Title, URL,
Products[], Hazards[], Remedies[]...) by fetching a live response through
the research tool. Not yet exercised by this project's own HTTP client
against the live API (the build sandbox blocks that host): the parsing is
tested against a recorded-shape fixture only.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.error import URLError

CPSC_URL = "https://www.saferproducts.gov/RestWebServices/Recall"
CACHE_TTL_SECONDS = 6 * 3600
MAX_RESULTS = 5
DISCLAIMER = (
    "Possible matches found by product name in the US CPSC public recall database. "
    "A match is not confirmation that your product is affected -- open the CPSC link and compare "
    "the model, dates and photos before acting."
)

_STOPWORDS = {
    "the", "and", "for", "with", "set", "pack", "pcs", "piece", "pieces", "new", "best",
    "premium", "pro", "plus", "mini", "large", "small", "of", "in", "a", "an",
}
_cache: dict[str, tuple[float, dict]] = {}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS and len(t) > 1]


def search_terms(product_name: str) -> list[str]:
    """Up to two ProductName queries, most specific first: the cleaned full
    name, then its last two words (usually the product noun, e.g.
    'Stainless Steel Garlic Press' -> 'garlic press')."""
    cleaned = re.sub(r"\([^)]*\)", " ", product_name)  # drop "(3-pack)" style suffixes
    words = _tokens(cleaned)
    if not words:
        return []
    terms = [" ".join(words)]
    if len(words) > 2:
        terms.append(" ".join(words[-2:]))
    return terms


def _fetch(term: str, timeout: int = 15) -> list[dict]:
    url = f"{CPSC_URL}?{urllib_parse.urlencode({'format': 'json', 'ProductName': term})}"
    req = urllib_request.Request(url, headers={"Accept": "application/json", "User-Agent": "commercesense-ai/1.0"})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data if isinstance(data, list) else []


def _names(items: object, key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(i.get(key)).strip() for i in items if isinstance(i, dict) and i.get(key)]


def _shape(record: dict, product_tokens: set[str], brand: str | None) -> dict:
    product_names = _names(record.get("Products"), "Name")
    haystack = " ".join([record.get("Title") or "", record.get("Description") or "", *product_names]).lower()
    matched = sorted(t for t in product_tokens if t in haystack)
    brand_hit = bool(brand) and brand.lower() in (
        haystack + " " + " ".join(_names(record.get("Manufacturers"), "Name") + _names(record.get("Retailers"), "Name"))
    ).lower()
    return {
        "recall_id": record.get("RecallID"),
        "recall_number": record.get("RecallNumber"),
        "recall_date": (record.get("RecallDate") or "")[:10] or None,
        "title": record.get("Title"),
        "url": record.get("URL"),
        "product_names": product_names,
        "hazards": _names(record.get("Hazards"), "Name"),
        "remedies": _names(record.get("Remedies"), "Name"),
        "matched_terms": matched,
        "brand_match": brand_hit,
    }


def check_recalls(product_name: str, brand: str | None = None, *, fetch=_fetch, use_cache: bool = True) -> dict:
    """Never raises. Returns {"available", "provenance": "LIVE", ...}.
    `fetch` is injectable so the logic is testable without network access."""
    terms = search_terms(product_name)
    now = datetime.now(timezone.utc).isoformat()
    base = {"provenance": "LIVE", "source": "US CPSC Recall Retrieval API (saferproducts.gov)",
            "queried_terms": terms, "retrieved_at": now, "disclaimer": DISCLAIMER}
    if not terms:
        return {**base, "available": False, "error": "Product name has no searchable words", "matches": []}

    cache_key = "|".join(terms) + "|" + (brand or "").lower()
    cached = _cache.get(cache_key)
    if use_cache and cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return {**cached[1], "provenance": "CACHED"}

    records: dict[object, dict] = {}
    errors: list[str] = []
    for term in terms:
        try:
            for rec in fetch(term):
                records.setdefault(rec.get("RecallID") or rec.get("RecallNumber"), rec)
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            errors.append(f"{term!r}: {exc}")

    if errors and not records:
        return {**base, "available": False, "error": "; ".join(errors), "matches": []}

    product_tokens = set(_tokens(re.sub(r"\([^)]*\)", " ", product_name)))
    shaped = [_shape(r, product_tokens, brand) for r in records.values()]
    # Keep only records that share at least two product words (or one word
    # when the name itself only has one), then brand hits first, newest first.
    need = 1 if len(product_tokens) < 2 else 2
    shaped = [s for s in shaped if len(s["matched_terms"]) >= need]
    shaped.sort(key=lambda s: s["recall_date"] or "", reverse=True)
    shaped.sort(key=lambda s: not s["brand_match"])

    result = {**base, "available": True, "error": "; ".join(errors) or None,
              "total_matches": len(shaped), "matches": shaped[:MAX_RESULTS]}
    _cache[cache_key] = (time.time(), result)
    return result
