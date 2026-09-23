from listing_engine import evaluate_listing, score_listing


GOOD_LISTING = dict(
    title="Premium Stainless Steel Garlic Press — Heavy-Duty Kitchen Tool",
    brand="AcmeBrand",
    product_type="Kitchen",
    bullets=[
        "PREMIUM MATERIAL — built to last through daily use",
        "DESIGNED FOR CONVENIENCE — makes everyday tasks easier",
        "SATISFACTION GUARANTEED — backed by our quality promise",
        "VERSATILE USE — perfect for home or gifting",
        "TRUSTED CHOICE — a top-rated pick in Kitchen",
    ],
    description="A thoughtfully designed kitchen tool built for reliability and ease of use, crafted with attention to detail.",
    attributes={"color": "Silver", "material": "Steel"},
    image_count=6,
    image_urls=[f"https://x/{i}.jpg" for i in range(6)],
)

POOR_LISTING = dict(
    title="Item1",
    brand="AcmeBrand",
    product_type="Kitchen",
    bullets=[],
    description="Good product.",
    attributes={},
    image_count=0,
    image_urls=[],
)


def test_good_listing_scores_high():
    rules = evaluate_listing(**GOOD_LISTING)
    result = score_listing(rules)
    assert result["score"] >= 80
    assert "images_missing" not in result["failed_rules"]


def test_poor_listing_scores_low_and_reports_failures():
    rules = evaluate_listing(**POOR_LISTING)
    result = score_listing(rules)
    assert result["score"] < 50
    assert "bullets_missing" in result["failed_rules"]
    assert "images_missing" in result["failed_rules"]
    assert "description_missing" not in result["failed_rules"]  # "Good product." is non-empty


def test_score_never_hides_calculation():
    rules = evaluate_listing(**POOR_LISTING)
    result = score_listing(rules)
    # every category must be individually visible, not just the total
    assert set(result["category_scores"].keys()) == {
        "completeness", "content_quality", "consistency", "keyword_hygiene", "media",
    }
    assert len(result["rule_detail"]) == len(rules)


def test_repeated_words_detected():
    rules = evaluate_listing(
        title="Best Best Garlic Press for your Kitchen",
        brand="AcmeBrand", product_type="Kitchen",
        bullets=GOOD_LISTING["bullets"], description=GOOD_LISTING["description"],
        attributes=GOOD_LISTING["attributes"], image_count=6, image_urls=GOOD_LISTING["image_urls"],
    )
    failed_and_warned = [r["rule_id"] for r in rules if not r["passed"]]
    assert "title_repeated_words" in failed_and_warned


def test_duplicate_bullets_detected():
    rules = evaluate_listing(
        title=GOOD_LISTING["title"], brand="AcmeBrand", product_type="Kitchen",
        bullets=["Same bullet text", "Same bullet text", "Third one"],
        description=GOOD_LISTING["description"], attributes=GOOD_LISTING["attributes"],
        image_count=6, image_urls=GOOD_LISTING["image_urls"],
    )
    failed_and_warned = [r["rule_id"] for r in rules if not r["passed"]]
    assert "bullets_duplicate" in failed_and_warned
