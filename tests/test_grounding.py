"""Grounding tests — the project's non-negotiable rule (CLAUDE.md rule 4,
extended here to the new modules): an AI-generated claim must be traceable
to real, verified data, or it gets stripped/rejected, never presented as
fact. These tests plant deliberately fabricated content and assert it gets
caught, the same way the existing agent/insight_agent.py tests do for the
Insight Agent.
"""

from listing_engine import check_rewrite_grounding


ORIGINAL_FIELDS = {
    "title": "Stainless Steel Garlic Press",
    "brand": "AcmeBrand",
    "bullets": "Dishwasher safe. Ergonomic handle. Holds 1 clove at a time.",
    "description": "A durable kitchen tool for everyday cooking.",
}


def test_valid_rewrite_with_no_new_numbers_is_grounded():
    proposed = "Premium Stainless Steel Garlic Press with an ergonomic handle, dishwasher safe."
    result = check_rewrite_grounding(ORIGINAL_FIELDS, proposed)
    assert result["grounded"] is True
    assert result["unsupported_numbers"] == []


def test_fabricated_number_is_rejected():
    # "10-year warranty" and "50% stronger" were never in the original data
    proposed = "Stainless Steel Garlic Press, backed by a 10-year warranty and 50% stronger than competitors."
    result = check_rewrite_grounding(ORIGINAL_FIELDS, proposed)
    assert result["grounded"] is False
    assert "10" in result["unsupported_numbers"]
    assert "50" in result["unsupported_numbers"]
    assert result["reason"] is not None


def test_number_that_actually_appears_in_original_is_allowed():
    # "1" appears in the original bullets ("Holds 1 clove at a time")
    proposed = "Garlic Press that holds 1 clove at a time, dishwasher safe."
    result = check_rewrite_grounding(ORIGINAL_FIELDS, proposed)
    assert result["grounded"] is True


def test_empty_citation_style_case_contains_no_numbers_is_trivially_grounded():
    proposed = "A reliable, ergonomic garlic press for everyday cooking."
    result = check_rewrite_grounding(ORIGINAL_FIELDS, proposed)
    assert result["grounded"] is True
