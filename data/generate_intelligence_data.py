"""
generate_intelligence_data.py — deterministic synthetic data for the four
intelligence modules (Listing, Pricing, Review, Inventory). Reuses the
existing 14 products from generate_synthetic_data.PRODUCT_PLAN -- no new
product model. Uses the SAME SEED but a dedicated random.Random() instance
so this never perturbs the already-verified daily_metrics/signal ground
truth that generate_synthetic_data.py produces.

Ground truth for the planted quality issues (deliberately independent of
the existing inventory/PPC/rank plants, for genuine cross-module variety)
is written to eval/labeled_set_intelligence.json.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "db"))
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligence"))
import db  # noqa: E402
import intelligence_db as idb  # noqa: E402
from review_engine import themes_for_category  # noqa: E402 -- single source of truth for theme vocab

EVAL_LABELS_PATH = Path(__file__).parent.parent / "eval" / "labeled_set_intelligence.json"

# Planted ground truth
POOR_LISTING_PRODUCTS = {"P001", "P004", "P009", "P012"}
BELOW_MARGIN_PRODUCTS = {"P003", "P007", "P013"}
EMERGING_ISSUE_PRODUCTS = {"P002": "warping", "P006": "flickering"}
NEGATIVE_CLUSTER_PRODUCTS = {"P008"}

POSITIVE_TEMPLATES = [
    "Really happy with the {theme} on this one.",
    "The {theme} exceeded my expectations.",
    "Great {theme}, would buy again.",
    "No complaints about the {theme} at all — solid purchase.",
    "Solid product overall, especially the {theme}.",
]
NEGATIVE_TEMPLATES = [
    "Disappointed with the {theme}.",
    "The {theme} was worse than I expected.",
    "Had real issues with the {theme}.",
    "Wouldn't recommend because of the {theme} problems.",
    "Started having {theme} issues after a short time.",
]
NEUTRAL_TEMPLATES = [
    "It's fine, does the job.",
    "Average product, nothing special either way.",
    "Works as described, no major issues.",
]

GOOD_TITLE_SUFFIXES = ["Premium", "Heavy-Duty", "Professional Grade", "Multi-Purpose"]


def _generate_listing(rng: random.Random, name: str, category: str, is_poor: bool) -> dict:
    if is_poor:
        title = name.split()[0]
        bullets: list[str] = []
        description = "Good product."
        image_count = rng.choice([0, 1])
        attributes = {"color": "N/A"}
    else:
        suffix = rng.choice(GOOD_TITLE_SUFFIXES)
        title = f"{name} — {suffix}, Amazon's Choice Quality"
        bullets = [
            f"PREMIUM {category.upper()} MATERIAL — built to last through daily use",
            "DESIGNED FOR CONVENIENCE — makes everyday tasks easier",
            "SATISFACTION GUARANTEED — backed by our quality promise",
            "VERSATILE USE — perfect for home, gifting, or everyday needs",
            f"TRUSTED CHOICE — a top-rated pick in {category}",
        ]
        description = (
            f"The {name} is thoughtfully designed for reliability and ease of use. "
            f"Crafted with attention to detail, it fits seamlessly into your "
            f"{category.lower()} routine. Backed by our commitment to quality, this "
            f"product is built to perform day after day."
        )
        image_count = rng.randint(5, 8)
        attributes = {"color": rng.choice(["Black", "White", "Silver", "Blue"]), "material": "Mixed"}

    return dict(
        title=title,
        brand="CommerceSense Demo Co.",
        product_type=category,
        bullets=bullets,
        description=description,
        backend_keywords=None,
        attributes=attributes,
        image_urls=[f"https://example.com/img/{i}.jpg" for i in range(image_count)],
        image_count=image_count,
        listing_status="ACTIVE",
    )


def _generate_pricing(rng: random.Random, base_price: float, below_margin: bool) -> tuple[dict, list[dict]]:
    cogs = round(base_price * rng.uniform(0.28, 0.38), 2)
    referral_fee_pct = 0.15
    # Fulfillment/other costs scale WITH price, not a flat dollar amount --
    # a flat $3-6.5 fee was disproportionate on the cheapest products in
    # this catalog ($9.99-$14.99), pushing their real margin below any
    # "healthy" target regardless of the below_margin plant. Percentage-
    # of-price costs keep the achievable margin range consistent across
    # the whole $9.99-$34.99 catalog.
    fulfillment_fee = round(base_price * rng.uniform(0.10, 0.18), 2)
    other_cost = round(base_price * rng.uniform(0.01, 0.04), 2)
    # Real achievable margin here is roughly 25-46% given the ranges
    # above. A wide gap between the two targets keeps both plants correct
    # with real headroom rather than hoping a narrow random draw lands
    # exactly right.
    target_margin_pct = 0.45 if below_margin else 0.20

    pricing_data = dict(
        cogs=cogs,
        referral_fee_pct=referral_fee_pct,
        fulfillment_fee=fulfillment_fee,
        other_cost=other_cost,
        target_margin_pct=target_margin_pct,
        currency="USD",
    )

    n_competitors = rng.randint(3, 5)
    center = base_price * (rng.uniform(0.75, 0.9) if below_margin else rng.uniform(0.9, 1.05))
    observations = []
    for i in range(n_competitors):
        price = round(center * rng.uniform(0.9, 1.1), 2)
        observations.append(
            dict(
                competitor=f"Competitor {chr(65 + i)}",
                price=price,
                currency="USD",
                source="synthetic",
                source_url=None,
                confidence="medium",
                is_verified=False,
            )
        )
    return pricing_data, observations


def _generate_reviews(
    rng: random.Random, category: str, emerging_theme: str | None, negative_cluster: bool
) -> list[dict]:
    themes = themes_for_category(category)
    today = date.today()
    n_reviews = rng.randint(35, 70)
    reviews = []

    for _ in range(n_reviews):
        days_ago = rng.randint(0, 89)
        review_date = today - timedelta(days=days_ago)

        if negative_cluster and rng.random() < 0.5:
            theme = rng.choice(themes)
            rating = rng.choice([1, 2, 2, 3])
            text = rng.choice(NEGATIVE_TEMPLATES).format(theme=theme)
        else:
            roll = rng.random()
            if roll < 0.72:
                rating = rng.choice([4, 5, 5])
                text = rng.choice(POSITIVE_TEMPLATES).format(theme=rng.choice(themes))
            elif roll < 0.88:
                rating = 3
                text = rng.choice(NEUTRAL_TEMPLATES)
            else:
                rating = rng.choice([1, 2])
                text = rng.choice(NEGATIVE_TEMPLATES).format(theme=rng.choice(themes))

        reviews.append(
            dict(
                rating=rating,
                review_text=text,
                review_date=review_date.isoformat(),
                verified_purchase=rng.random() < 0.9,
                source="synthetic",
            )
        )

    if emerging_theme:
        # Deterministic injection, not probabilistic -- the same
        # "strongly distinct, not left to RNG variance" design already
        # used for the original stockout/PPC/rank plants in
        # generate_synthetic_data.py. Exactly 7 reviews, all dated in the
        # last 20 days, all mentioning the theme -> a real, robust spike
        # (previous=0, current=7) regardless of how the random draw for
        # the rest of this product's reviews happened to land.
        for i in range(7):
            days_ago = rng.randint(0, 20)
            reviews.append(
                dict(
                    rating=rng.choice([1, 2]),
                    review_text=NEGATIVE_TEMPLATES[rng.randrange(len(NEGATIVE_TEMPLATES))].format(theme=emerging_theme),
                    review_date=(today - timedelta(days=days_ago)).isoformat(),
                    verified_purchase=rng.random() < 0.9,
                    source="synthetic",
                )
            )

    return reviews


def generate_intelligence_data(product_plan: list[tuple]) -> None:
    from generate_synthetic_data import SEED

    rng = random.Random(SEED)  # dedicated stream, never shared with the caller's rng

    db.init_db()
    conn = db.get_connection()
    for table in (
        "listing_recommendations", "listing_audits", "listing_data",
        "pricing_analyses", "pricing_observations", "pricing_data",
        "review_analyses", "review_items",
        "inventory_config",
        "intelligence_runs",
    ):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

    ground_truth = []

    for product_id, name, category, base_price, _existing_planted_signal in product_plan:
        is_poor_listing = product_id in POOR_LISTING_PRODUCTS
        listing = _generate_listing(rng, name, category, is_poor_listing)
        idb.upsert_listing_data(product_id, **listing)

        below_margin = product_id in BELOW_MARGIN_PRODUCTS
        pricing_data, observations = _generate_pricing(rng, base_price, below_margin)
        idb.upsert_pricing_data(product_id, **pricing_data)
        for obs in observations:
            idb.insert_pricing_observation(
                product_id, obs["competitor"], obs["price"], obs["currency"],
                obs["source"], obs["source_url"], date.today().isoformat(),
                obs["confidence"], obs["is_verified"],
            )

        emerging_theme = EMERGING_ISSUE_PRODUCTS.get(product_id)
        negative_cluster = product_id in NEGATIVE_CLUSTER_PRODUCTS
        for r in _generate_reviews(rng, category, emerging_theme, negative_cluster):
            idb.insert_review_item(
                product_id, r["rating"], r["review_text"], r["review_date"],
                r["verified_purchase"], r["source"],
            )

        idb.upsert_inventory_config(
            product_id,
            lead_time_days=rng.randint(7, 21),
            safety_days=rng.randint(3, 10),
            moq=rng.choice([25, 50, 100]),
            reorder_multiple=rng.choice([10, 25, 50]),
            target_service_level=0.95,
        )

        ground_truth.append(
            {
                "product_id": product_id,
                "name": name,
                "poor_listing": is_poor_listing,
                "below_margin_floor": below_margin,
                "emerging_review_issue": emerging_theme,
                "negative_review_cluster": negative_cluster,
            }
        )

    EVAL_LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_LABELS_PATH.open("w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Generated listing/pricing/review/inventory data for {len(product_plan)} products.")
    print(f"Ground-truth labels written to {EVAL_LABELS_PATH}")


if __name__ == "__main__":
    from generate_synthetic_data import PRODUCT_PLAN

    generate_intelligence_data(PRODUCT_PLAN)
