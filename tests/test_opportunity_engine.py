from opportunity_engine import compute_attention_score


def test_healthy_product_scores_zero():
    result = compute_attention_score(
        inventory_category="HEALTHY", negative_review_pct=5, has_emerging_review_issue=False,
        listing_score=90, price_state="HEALTHY_RANGE", existing_signals=[],
    )
    assert result["attention_score"] == 0
    assert all(v == 0 for v in result["components"].values())


def test_components_are_individually_visible_and_sum_to_total():
    result = compute_attention_score(
        inventory_category="STOCKOUT_RISK", negative_review_pct=35, has_emerging_review_issue=True,
        listing_score=30, price_state="BELOW_MARGIN_FLOOR",
        existing_signals=[{"severity": "high"}],
    )
    assert result["components"]["inventory_risk"] == 30
    assert result["components"]["review_risk"] == 25  # capped at 25 (15+10)
    assert result["components"]["listing_issues"] == 20
    assert result["components"]["pricing_pressure"] == 15
    assert result["components"]["existing_signals"] == 6
    assert result["attention_score"] == sum(result["components"].values())


def test_attention_score_capped_at_100():
    result = compute_attention_score(
        inventory_category="STOCKOUT_RISK", negative_review_pct=50, has_emerging_review_issue=True,
        listing_score=0, price_state="BELOW_MARGIN_FLOOR",
        existing_signals=[{"severity": "high"}] * 5,
    )
    assert result["attention_score"] <= 100


def test_none_inputs_never_crash_and_contribute_zero():
    result = compute_attention_score(
        inventory_category="NO_DATA", negative_review_pct=None, has_emerging_review_issue=False,
        listing_score=None, price_state="UNKNOWN", existing_signals=[],
    )
    assert result["attention_score"] == 0
