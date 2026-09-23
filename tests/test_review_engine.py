from datetime import date, timedelta

from review_engine import (
    detect_emerging_issues,
    discover_candidate_words,
    rating_stats,
    review_velocity,
    theme_frequency,
    themes_for_category,
)


def _mk(rating, text, days_ago, rid=None):
    return {"id": rid, "rating": rating, "review_text": text, "review_date": (date.today() - timedelta(days=days_ago)).isoformat()}


def test_rating_stats_empty():
    result = rating_stats([])
    assert result["total_reviews"] == 0
    assert result["avg_rating"] is None


def test_rating_stats_basic():
    reviews = [_mk(5, "great", 1), _mk(5, "great", 2), _mk(1, "bad", 3), _mk(3, "ok", 4)]
    result = rating_stats(reviews)
    assert result["total_reviews"] == 4
    assert result["avg_rating"] == 3.5
    assert result["negative_pct"] == 25.0


def test_review_velocity_insufficient_data_guard():
    reviews = [_mk(5, "great", 1), _mk(4, "good", 2)]
    result = review_velocity(reviews, window_days=30)
    assert result["trend"] == "insufficient_data"


def test_review_velocity_rising_trend():
    # previous window = days_ago in [30, 60); current window = [0, 30)
    reviews = (
        [_mk(3, "meh", d) for d in [32, 38, 44, 50, 56, 58]]  # 6 in previous window
        + [_mk(3, "meh", d) for d in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]]  # 10 in current window
    )
    result = review_velocity(reviews, window_days=30)
    assert result["current_count"] == 10
    assert result["previous_count"] == 6
    assert result["trend"] == "rising"
    assert result["pct_change"] > 0


def test_theme_frequency_only_reports_real_matches_with_real_evidence():
    reviews = [
        _mk(2, "The battery life was disappointing.", 1, rid=1),
        _mk(5, "Loved the battery life on this.", 2, rid=2),
        _mk(4, "No complaints about size.", 3, rid=3),
    ]
    themes = theme_frequency(reviews, ["battery life", "connectivity"])
    assert len(themes) == 1  # connectivity never mentioned -> must not appear
    bl = themes[0]
    assert bl["theme"] == "battery life"
    assert bl["mentions"] == 2
    assert bl["negative"] == 1
    assert bl["positive"] == 1
    # evidence must reference the actual reviews, not fabricated text
    evidence_ids = {e["id"] for e in bl["evidence"]}
    assert evidence_ids == {1, 2}


def test_discover_candidate_words_excludes_stopwords_and_short_words():
    reviews = [_mk(2, "This product had real leaking issues after a short time.", d) for d in [1, 2, 3]]
    words = discover_candidate_words(reviews)
    assert "leaking" in words
    assert "this" not in words  # stopword
    assert "had" not in words  # too short


def test_discover_candidate_words_filters_low_frequency_noise():
    # a word mentioned only once or twice shouldn't become a candidate --
    # it's the kind of incidental mention that produces false emerging-
    # issue alerts with no real signal behind them.
    reviews = [_mk(3, "There was a slight squeaking noise.", 1)]
    assert "squeaking" not in discover_candidate_words(reviews)


def test_detect_emerging_issue_requires_a_real_spike():
    # zero before, a real cluster in the last 30 days -> should flag
    reviews = [_mk(2, "Started warping after use.", d) for d in [2, 5, 8, 11, 14]]
    result = detect_emerging_issues(reviews, "warping", window_days=30)
    assert result is not None
    assert result["previous_period_mentions"] == 0
    assert result["current_period_mentions"] == 5
    assert "warping" in result["explanation"]


def test_detect_emerging_issue_below_min_total_mentions_is_none():
    # only 3 total mentions -- not enough signal either way
    reviews = [_mk(2, "Started warping after use.", d) for d in [2, 5, 8]]
    assert detect_emerging_issues(reviews, "warping", window_days=30) is None


def test_detect_emerging_issue_returns_none_when_stable():
    # enough total mentions to clear the noise floor, but evenly spread
    # (not a real spike) -> must not flag
    reviews = [_mk(2, "minor durability concern", d) for d in [5, 10, 40, 45, 70, 80]]
    result = detect_emerging_issues(reviews, "durability", window_days=30)
    assert result is None


def test_themes_for_category_fallback():
    assert themes_for_category("Nonexistent Category") == ["quality", "value", "durability"]
    assert "battery life" in themes_for_category("Electronics")
