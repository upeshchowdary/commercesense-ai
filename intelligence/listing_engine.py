"""
listing_engine.py — deterministic Listing Intelligence rule engine and
scoring. Pure functions: no I/O, no LLM. This is a "CommerceSense
heuristic," not an official Amazon ranking score — never presented as one.
"""

from __future__ import annotations

import re
from typing import TypedDict

CATEGORY_WEIGHTS = {
    "completeness": 25,
    "content_quality": 25,
    "consistency": 20,
    "keyword_hygiene": 15,
    "media": 15,
}


class RuleResult(TypedDict):
    rule_id: str
    category: str
    passed: bool
    severity: str  # "fail" | "warn"
    message: str
    deduction: int  # points off that category's 100, only applied if not passed


def _has_repeated_words(text: str, min_len: int = 4) -> bool:
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", text) if len(w) >= min_len]
    seen = set()
    for w in words:
        if w in seen:
            return True
        seen.add(w)
    return False


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def evaluate_listing(
    title: str,
    brand: str,
    product_type: str,
    bullets: list[str],
    description: str,
    attributes: dict,
    image_count: int,
    image_urls: list[str],
) -> list[RuleResult]:
    results: list[RuleResult] = []

    def add(rule_id: str, category: str, passed: bool, severity: str, message: str, deduction: int = 0) -> None:
        results.append(
            RuleResult(rule_id=rule_id, category=category, passed=passed, severity=severity,
                       message=message, deduction=0 if passed else deduction)
        )

    # --- TITLE ---
    add("title_empty", "completeness", bool(title.strip()), "fail", "Title is empty.", 40)
    add("title_length", "content_quality", 15 <= len(title) <= 200, "warn",
        f"Title length is {len(title)} characters (recommended 15-200).", 35)
    add("title_repeated_words", "consistency", not _has_repeated_words(title), "warn",
        "Title contains repeated words.", 15)
    punct_count = len(re.findall(r"[!?$%*]{1,}", title))
    add("title_excessive_punctuation", "consistency", punct_count <= 1, "warn",
        "Title has excessive punctuation.", 10)
    add("title_excessive_caps", "consistency", _caps_ratio(title) <= 0.5, "warn",
        "Title is more than half uppercase.", 15)
    add("title_missing_brand", "keyword_hygiene", brand.lower() in title.lower(), "warn",
        "Title does not mention the brand.", 15)
    add("title_missing_product_type", "keyword_hygiene", product_type.lower() in title.lower(), "warn",
        "Title does not mention the product type/category.", 15)

    # --- BULLETS ---
    add("bullets_missing", "completeness", len(bullets) > 0, "fail", "No bullet points.", 50)
    add("bullets_too_few", "completeness", len(bullets) >= 3, "warn",
        f"Only {len(bullets)} bullet point(s) (recommended 3-5+).", 15)
    long_bullets = [b for b in bullets if len(b) > 500]
    add("bullets_too_long", "content_quality", len(long_bullets) == 0, "warn",
        f"{len(long_bullets)} bullet(s) exceed 500 characters.", 10)
    short_bullets = [b for b in bullets if 0 < len(b) < 10]
    add("bullets_too_short", "content_quality", len(short_bullets) == 0, "warn",
        f"{len(short_bullets)} bullet(s) are under 10 characters.", 10)
    add("bullets_duplicate", "consistency", len(bullets) == len(set(bullets)), "warn",
        "Duplicate bullet content detected.", 15)

    # --- DESCRIPTION ---
    add("description_missing", "completeness", len(description.strip()) > 0, "fail", "No description.", 20)
    add("description_too_short", "content_quality", len(description) >= 50, "warn",
        f"Description is {len(description)} characters (recommended 50+).", 20)

    # --- ATTRIBUTES ---
    add("attributes_missing", "completeness", len(attributes) > 0, "warn", "No product attributes provided.", 10)

    # --- IMAGES ---
    add("images_missing", "media", image_count > 0, "fail", "No images.", 80)
    add("images_too_few", "media", image_count >= 4, "warn",
        f"Only {image_count} image(s) (recommended 4+).", 25)
    add("images_duplicate", "media", len(image_urls) == len(set(image_urls)), "warn",
        "Duplicate image URLs detected.", 15)

    return results


def extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def check_rewrite_grounding(original_fields: dict[str, str], proposed_text: str) -> dict:
    """A rewrite must not invent a number (dimension, quantity, percentage,
    warranty length, etc.) that doesn't appear anywhere in the original,
    verified listing fields. This is the listing-rewrite equivalent of
    agent/insight_agent.py's source-match grounding guardrail: a fluent
    proposal is not the same thing as an honest one."""
    original_combined = " ".join(str(v) for v in original_fields.values())
    original_numbers = extract_numbers(original_combined)
    proposed_numbers = extract_numbers(proposed_text)
    unsupported = sorted(proposed_numbers - original_numbers)
    return {
        "grounded": len(unsupported) == 0,
        "unsupported_numbers": unsupported,
        "reason": (
            None if not unsupported
            else f"Proposed text introduces number(s) not present in the original listing: {', '.join(unsupported)}"
        ),
    }


def score_listing(rules: list[RuleResult]) -> dict:
    category_scores: dict[str, int] = {c: 100 for c in CATEGORY_WEIGHTS}
    for r in rules:
        if not r["passed"]:
            category_scores[r["category"]] = max(0, category_scores[r["category"]] - r["deduction"])

    overall = sum(category_scores[c] * (w / 100) for c, w in CATEGORY_WEIGHTS.items())
    failed_rules = [r["rule_id"] for r in rules if not r["passed"] and r["severity"] == "fail"]
    warnings = [r["rule_id"] for r in rules if not r["passed"] and r["severity"] == "warn"]
    passed_rules = [r["rule_id"] for r in rules if r["passed"]]

    return {
        "score": round(overall),
        "category_scores": category_scores,
        "failed_rules": failed_rules,
        "warnings": warnings,
        "passed_rules": passed_rules,
        "rule_detail": rules,
    }
