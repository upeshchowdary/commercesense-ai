"""
review_engine.py — deterministic Review Intelligence: rating statistics,
velocity, and theme extraction. Theme detection is plain keyword/phrase
frequency against a curated vocabulary plus a simple frequency-based
discovery pass for anything not in that vocabulary — deliberately no
sentence-transformers/sklearn dependency; this fully satisfies "themes
must emerge from actual review text, deterministically" without a heavy
ML dependency for a hackathon-scale dataset.

A "review" here is any dict/Row with: rating (int), review_text (str),
review_date (ISO date string), and optionally id.
"""

from __future__ import annotations

from datetime import date, timedelta

THEME_VOCAB: dict[str, list[str]] = {
    "Kitchen": ["durability", "ease of use", "size", "quality", "packaging"],
    "Electronics": ["battery life", "connectivity", "build quality", "overheating", "setup"],
    "Beauty": ["texture", "scent", "effectiveness", "packaging", "skin reaction"],
    "Sports": ["durability", "grip", "comfort", "material quality", "smell"],
    "Home & Garden": ["durability", "weather resistance", "brightness", "assembly", "value"],
}
DEFAULT_THEMES = ["quality", "value", "durability"]

_STOPWORDS = {
    "this", "that", "with", "have", "just", "very", "really", "product",
    "after", "started", "issues", "problems", "worse", "expected", "would",
    "recommend", "because", "wouldn't", "disappointed", "about", "which",
    "overall", "solid", "great", "happy", "again", "loved", "buying",
    "purchase", "exceeded", "expectations", "complaints", "special",
    "either", "average", "described", "major", "works", "especially",
    "trusted", "choice", "worth",
}


def themes_for_category(category: str) -> list[str]:
    return THEME_VOCAB.get(category, DEFAULT_THEMES)


def rating_stats(reviews: list[dict]) -> dict:
    if not reviews:
        return {"total_reviews": 0, "avg_rating": None, "rating_distribution": {}, "negative_pct": None}
    total = len(reviews)
    distribution = {str(s): 0 for s in range(1, 6)}
    for r in reviews:
        distribution[str(r["rating"])] += 1
    avg_rating = round(sum(r["rating"] for r in reviews) / total, 2)
    negative = distribution["1"] + distribution["2"]
    return {
        "total_reviews": total,
        "avg_rating": avg_rating,
        "rating_distribution": {k: {"count": v, "pct": round(v / total * 100, 1)} for k, v in distribution.items()},
        "negative_pct": round(negative / total * 100, 1),
    }


def _in_window(review_date_str: str, start_days_ago: int, end_days_ago: int, today: date) -> bool:
    try:
        d = date.fromisoformat(review_date_str)
    except ValueError:
        return False
    days_ago = (today - d).days
    return end_days_ago <= days_ago < start_days_ago


def review_velocity(reviews: list[dict], window_days: int = 30, today: date | None = None) -> dict:
    today = today or date.today()
    current = [r for r in reviews if _in_window(r["review_date"], window_days, 0, today)]
    previous = [r for r in reviews if _in_window(r["review_date"], window_days * 2, window_days, today)]

    if len(reviews) < 5:
        return {"window_days": window_days, "current_count": len(current), "previous_count": len(previous),
                "pct_change": None, "trend": "insufficient_data"}

    pct_change = None
    if len(previous) > 0:
        pct_change = round((len(current) - len(previous)) / len(previous) * 100, 1)
    elif len(current) > 0:
        pct_change = None  # can't compute a % change from a zero base -- report counts, not a fabricated infinite %

    if len(current) > len(previous) * 1.2 if previous else len(current) > 3:
        trend = "rising"
    elif previous and len(current) < len(previous) * 0.8:
        trend = "falling"
    else:
        trend = "stable"

    return {"window_days": window_days, "current_count": len(current), "previous_count": len(previous),
            "pct_change": pct_change, "trend": trend}


def theme_frequency(reviews: list[dict], candidate_themes: list[str]) -> list[dict]:
    results = []
    for theme in candidate_themes:
        theme_lower = theme.lower()
        matches = [r for r in reviews if theme_lower in r["review_text"].lower()]
        if not matches:
            continue
        negative = sum(1 for r in matches if r["rating"] <= 2)
        neutral = sum(1 for r in matches if r["rating"] == 3)
        positive = sum(1 for r in matches if r["rating"] >= 4)
        evidence = [
            {"id": r.get("id"), "rating": r["rating"], "review_text": r["review_text"], "review_date": r["review_date"]}
            for r in sorted(matches, key=lambda r: r["review_date"], reverse=True)[:5]
        ]
        results.append({
            "theme": theme, "mentions": len(matches), "negative": negative,
            "neutral": neutral, "positive": positive, "evidence": evidence,
        })
    results.sort(key=lambda t: t["mentions"], reverse=True)
    return results


def discover_candidate_words(reviews: list[dict], top_n: int = 8, min_count: int = 3) -> list[str]:
    """Deterministic frequency count over words >=5 chars, excluding a
    small stopword list -- a lightweight, dependency-free stand-in for
    "theme discovery" that still only ever surfaces words that actually
    appear in the supplied review text. min_count filters out incidental
    one-off words before they're even considered a candidate theme -- a
    word with only 1-2 total mentions has no real signal either way, and
    including it as an emerging-issue candidate mostly just adds noise
    (a low-frequency word landing entirely within a 30-day window by
    chance is not a meaningfully rare event)."""
    counts: dict[str, int] = {}
    for r in reviews:
        for word in r["review_text"].lower().replace(".", " ").replace(",", " ").split():
            word = word.strip("'\"")
            if len(word) >= 5 and word not in _STOPWORDS:
                counts[word] = counts.get(word, 0) + 1
    ranked = sorted(((w, c) for w, c in counts.items() if c >= min_count), key=lambda kv: kv[1], reverse=True)
    return [w for w, _ in ranked[:top_n]]


def detect_emerging_issues(
    reviews: list[dict], theme: str, window_days: int = 30, today: date | None = None, min_total_mentions: int = 5,
) -> dict | None:
    today = today or date.today()
    theme_lower = theme.lower()
    matches = [r for r in reviews if theme_lower in r["review_text"].lower()]
    if len(matches) < min_total_mentions:
        # Too little total signal either way to call this "emerging" --
        # this guards BOTH fixed category-vocabulary themes and
        # discovered words the same way, since a theme with only a few
        # total mentions landing in one window by chance isn't a real
        # spike, just noise from the random review-date distribution.
        return None

    current = sum(1 for r in matches if _in_window(r["review_date"], window_days, 0, today))
    previous = sum(1 for r in matches if _in_window(r["review_date"], window_days * 2, window_days, today))

    # Thresholds deliberately conservative: with ~14 products x up to a
    # dozen candidate themes each checked per run, a loose threshold
    # produces false alarms purely from random date placement even for
    # themes with no real trend. Requiring a larger current count (not
    # just a ratio) keeps a handful of ordinary mentions clustering by
    # chance from reading as "emerging."
    is_emerging = (previous == 0 and current >= 5) or (previous >= 1 and current >= previous * 3 and current >= 6)
    if not is_emerging:
        return None
    return {
        "theme": theme,
        "previous_period_mentions": previous,
        "current_period_mentions": current,
        "window_days": window_days,
        "explanation": (
            f"Mentions of '{theme}' increased from {previous} to {current} between the "
            f"previous and current {window_days}-day periods."
        ),
    }
