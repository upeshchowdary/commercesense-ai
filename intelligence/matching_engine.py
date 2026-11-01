"""
matching_engine.py — 3-Tier Competitor Matching Taxonomy for CommerceSense AI v3.

Taxonomy:
  - TIER 1: SAME_ASIN (Direct Buy Box competition on identical catalog listing).
  - TIER 2: EXACT_EQUIVALENT (Different ASIN, verified same item/variant using
    GTIN/EAN/UPC or brand + manufacturer model + hard variant constraints).
  - TIER 3: SUBSTITUTE (Category substitute solving similar need, different brand/spec).

Strict Invariant:
  Substitutes (Tier 3) are strictly excluded from direct competitor medians and direct pricing decisions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import rapidfuzz.fuzz as fuzz


class MatchTier(str, Enum):
    TIER_1_SAME_ASIN = "TIER_1_SAME_ASIN"
    TIER_2_EXACT_EQUIVALENT = "TIER_2_EXACT_EQUIVALENT"
    TIER_3_SUBSTITUTE = "TIER_3_SUBSTITUTE"


class MatchMethod(str, Enum):
    EXACT_ASIN = "EXACT_ASIN"
    IDENTIFIER_GTIN = "IDENTIFIER_GTIN"
    SPEC_HARD_CONSTRAINT = "SPEC_HARD_CONSTRAINT"
    RAPIDFUZZ_SIMILARITY = "RAPIDFUZZ_SIMILARITY"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


@dataclass
class MatchResult:
    candidate_asin: str
    candidate_title: str
    match_tier: MatchTier
    match_confidence: str  # high, medium, low
    match_method: MatchMethod
    score: float  # 0.0 - 100.0
    matched_fields: List[str] = field(default_factory=list)
    mismatched_fields: List[str] = field(default_factory=list)
    seller_confirmed: Optional[bool] = None
    reviewed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_asin": self.candidate_asin,
            "candidate_title": self.candidate_title,
            "match_tier": self.match_tier.value,
            "match_confidence": self.match_confidence,
            "match_method": self.match_method.value,
            "score": round(self.score, 1),
            "matched_fields": self.matched_fields,
            "mismatched_fields": self.mismatched_fields,
            "seller_confirmed": self.seller_confirmed,
            "reviewed_at": self.reviewed_at,
        }


# Normalization helpers
def _normalize_str(val: Optional[str]) -> str:
    if not val:
        return ""
    # Lowercase, strip punctuation except alphanumeric and spaces
    s = str(val).lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def _extract_pack_count(text: str) -> Optional[int]:
    """Extracts pack/count integers from title (e.g. 'Pack of 2', '2-pack', 'Set of 4')."""
    lower = text.lower()
    m = re.search(r"\b(?:pack of|set of|count of)\s*(\d+)\b", lower)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d+)\s*(?:pack|pk|pcs|pieces|count)\b", lower)
    if m:
        return int(m.group(1))
    return None


def _extract_size_or_weight(text: str) -> Optional[str]:
    """Extracts size/weight units (e.g. '500ml', '100g', '10 oz')."""
    lower = text.lower()
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(ml|l|liter|litres|g|kg|gram|oz|ounce|lbs|pound)\b", lower)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return None


def classify_competitor_match(
    target_asin: str,
    target_title: str,
    target_brand: Optional[str],
    candidate_asin: str,
    candidate_title: str,
    candidate_brand: Optional[str],
    target_identifiers: Optional[Dict[str, str]] = None,
    candidate_identifiers: Optional[Dict[str, str]] = None,
    target_attributes: Optional[Dict[str, Any]] = None,
    candidate_attributes: Optional[Dict[str, Any]] = None,
) -> MatchResult:
    """Classifies a candidate competitor against a seller target product.
    Strictly differentiates:
      - Tier 1: Same ASIN
      - Tier 2: Exact Equivalent (strict constraints on pack, size, brand/model)
      - Tier 3: Category Substitute (excluded from direct medians)
    """
    matched: List[str] = []
    mismatched: List[str] = []

    # 1. Step 1: Same ASIN (Level 1)
    if target_asin and candidate_asin and target_asin.strip().upper() == candidate_asin.strip().upper():
        matched.append("asin")
        return MatchResult(
            candidate_asin=candidate_asin,
            candidate_title=candidate_title,
            match_tier=MatchTier.TIER_1_SAME_ASIN,
            match_confidence="high",
            match_method=MatchMethod.EXACT_ASIN,
            score=100.0,
            matched_fields=["asin"],
            mismatched_fields=[],
        )

    # 2. Step 2: Exact Barcode / Identifier Match (GTIN / EAN / UPC)
    t_ids = target_identifiers or {}
    c_ids = candidate_identifiers or {}
    for id_key in ("gtin", "ean", "upc", "isbn"):
        val_t = t_ids.get(id_key)
        val_c = c_ids.get(id_key)
        if val_t and val_c and str(val_t).strip() == str(val_c).strip():
            matched.append(f"identifier_{id_key}")
            return MatchResult(
                candidate_asin=candidate_asin,
                candidate_title=candidate_title,
                match_tier=MatchTier.TIER_2_EXACT_EQUIVALENT,
                match_confidence="high",
                match_method=MatchMethod.IDENTIFIER_GTIN,
                score=98.0,
                matched_fields=matched,
                mismatched_fields=[],
            )

    # 3. Step 3: Hard Variant Constraints Check (Pack size & Size/Volume)
    t_pack = _extract_pack_count(target_title)
    c_pack = _extract_pack_count(candidate_title)
    if t_pack is not None and c_pack is not None:
        if t_pack != c_pack:
            mismatched.append(f"pack_count (target: {t_pack} vs candidate: {c_pack})")
            # Pack mismatch is a HARD mismatch: automatically degrades candidate to Substitute!
            return MatchResult(
                candidate_asin=candidate_asin,
                candidate_title=candidate_title,
                match_tier=MatchTier.TIER_3_SUBSTITUTE,
                match_confidence="medium",
                match_method=MatchMethod.SPEC_HARD_CONSTRAINT,
                score=45.0,
                matched_fields=matched,
                mismatched_fields=mismatched,
            )
        else:
            matched.append(f"pack_count ({t_pack})")

    t_size = _extract_size_or_weight(target_title)
    c_size = _extract_size_or_weight(candidate_title)
    if t_size is not None and c_size is not None:
        if t_size != c_size:
            mismatched.append(f"size_volume (target: {t_size} vs candidate: {c_size})")
            # Size mismatch is a hard constraint mismatch
            return MatchResult(
                candidate_asin=candidate_asin,
                candidate_title=candidate_title,
                match_tier=MatchTier.TIER_3_SUBSTITUTE,
                match_confidence="medium",
                match_method=MatchMethod.SPEC_HARD_CONSTRAINT,
                score=50.0,
                matched_fields=matched,
                mismatched_fields=mismatched,
            )
        else:
            matched.append(f"size_volume ({t_size})")

    # 4. Step 4: Brand Matching
    norm_t_brand = _normalize_str(target_brand)
    norm_c_brand = _normalize_str(candidate_brand)
    same_brand = False
    if norm_t_brand and norm_c_brand:
        if norm_t_brand == norm_c_brand or norm_t_brand in norm_c_brand or norm_c_brand in norm_t_brand:
            same_brand = True
            matched.append("brand")
        else:
            mismatched.append("brand")

    # 5. Step 5: RapidFuzz Normalized Title & Token Match
    norm_t_title = _normalize_str(target_title)
    norm_c_title = _normalize_str(candidate_title)
    token_set_ratio = fuzz.token_set_ratio(norm_t_title, norm_c_title)
    token_sort_ratio = fuzz.token_sort_ratio(norm_t_title, norm_c_title)
    overall_sim = (token_set_ratio * 0.6) + (token_sort_ratio * 0.4)

    # Decision Matrix
    if same_brand and overall_sim >= 85.0:
        matched.append(f"title_similarity ({overall_sim:.1f}%)")
        return MatchResult(
            candidate_asin=candidate_asin,
            candidate_title=candidate_title,
            match_tier=MatchTier.TIER_2_EXACT_EQUIVALENT,
            match_confidence="high" if overall_sim >= 92.0 else "medium",
            match_method=MatchMethod.RAPIDFUZZ_SIMILARITY,
            score=overall_sim,
            matched_fields=matched,
            mismatched_fields=mismatched,
        )
    elif same_brand and overall_sim >= 65.0:
        matched.append("brand")
        return MatchResult(
            candidate_asin=candidate_asin,
            candidate_title=candidate_title,
            match_tier=MatchTier.TIER_3_SUBSTITUTE,
            match_confidence="medium",
            match_method=MatchMethod.RAPIDFUZZ_SIMILARITY,
            score=overall_sim,
            matched_fields=matched,
            mismatched_fields=mismatched,
        )
    else:
        # Different brand or low similarity
        tier = MatchTier.TIER_3_SUBSTITUTE if overall_sim >= 50.0 else MatchTier.TIER_3_SUBSTITUTE
        conf = "low" if overall_sim < 60.0 else "medium"
        return MatchResult(
            candidate_asin=candidate_asin,
            candidate_title=candidate_title,
            match_tier=tier,
            match_confidence=conf,
            match_method=MatchMethod.RAPIDFUZZ_SIMILARITY,
            score=overall_sim,
            matched_fields=matched,
            mismatched_fields=mismatched,
        )


def evaluate_candidate_matches(
    target_product: Any,
    candidate_catalog: List[Any],
) -> List[MatchResult]:
    """Ranks and classifies all candidate products against a seller product."""
    results: List[MatchResult] = []
    t_dict = dict(target_product) if hasattr(target_product, "keys") else (target_product if isinstance(target_product, dict) else {})
    t_asin = t_dict.get("asin") or t_dict.get("product_id") or ""
    t_title = t_dict.get("name") or t_dict.get("title") or ""
    t_brand = t_dict.get("brand") or ""

    for cand in candidate_catalog:
        c_dict = dict(cand) if hasattr(cand, "keys") else (cand if isinstance(cand, dict) else {})
        c_asin = c_dict.get("asin") or c_dict.get("product_id") or ""
        c_title = c_dict.get("name") or c_dict.get("title") or ""
        c_brand = c_dict.get("brand") or ""
        res = classify_competitor_match(
            target_asin=t_asin,
            target_title=t_title,
            target_brand=t_brand,
            candidate_asin=c_asin,
            candidate_title=c_title,
            candidate_brand=c_brand,
            target_identifiers=t_dict.get("identifiers"),
            candidate_identifiers=c_dict.get("identifiers"),
            target_attributes=t_dict.get("attributes"),
            candidate_attributes=c_dict.get("attributes"),
        )
        results.append(res)

    # Sort results by tier (Tier 1 > Tier 2 > Tier 3) and score descending
    tier_order = {MatchTier.TIER_1_SAME_ASIN: 1, MatchTier.TIER_2_EXACT_EQUIVALENT: 2, MatchTier.TIER_3_SUBSTITUTE: 3}
    results.sort(key=lambda r: (tier_order.get(r.match_tier, 99), -r.score))
    return results
