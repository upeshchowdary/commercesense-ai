"""
test_market_radar_and_opportunities.py — Comprehensive Test Suite for Phase 4.

Covers:
  1. GDELT 2.0 Doc API ingestion & PUBLIC_NEWS provenance.
  2. Curated Trade / Regulatory RSS feed XML parsing.
  3. Google Trends CSV multi-timeline parser & SELLER_INPUT provenance.
  4. Brand Analytics Search Terms & Search Query Performance parsing.
  5. Granular Brand Registry capability status (NEEDS_BRAND_REGISTRY).
  6. 6-Dimension Opportunity scoring engine & GO / CONDITIONAL_GO / NO_GO / INSUFFICIENT_EVIDENCE verdicts.
  7. Inviolable margin floor override in opportunity scoring.
  8. Market Radar & Opportunity API endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from intelligence.opportunity_evaluator import (
    OpportunityVerdict,
    evaluate_product_opportunity,
)
from providers.brand_analytics import (
    get_brand_analytics_status,
    parse_brand_analytics_search_terms,
    parse_search_query_performance,
)
from providers.market_radar import (
    fetch_regulatory_insights,
    parse_google_trends_csv,
    parse_rss_feed_content,
    query_gdelt_news,
)
from providers.provenance import ProvenanceEnvelope

client = TestClient(app)


# =====================================================================
# 1. GDELT 2.0 News Ingestion
# =====================================================================

def test_gdelt_news_fallback_and_envelope():
    res = query_gdelt_news("kitchen gadgets", max_records=5, use_mock_fallback=True)
    assert "envelope" in res
    assert res["envelope"]["source_type"] == "PUBLIC_NEWS"
    articles = res["articles"]
    assert len(articles) > 0
    first = articles[0]
    assert "title" in first
    assert "url" in first
    assert "domain" in first


# =====================================================================
# 2. Curated Trade / Regulatory RSS Feeds
# =====================================================================

def test_parse_rss_feed_content_xml():
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>CPSC Consumer Safety Recalls</title>
        <item>
          <title>Recall Notice: Stainless Steel Garlic Press Defect</title>
          <link>https://www.cpsc.gov/recalls/press-defect</link>
          <description>Defective hinge pins pose pinch hazard to consumers.</description>
          <pubDate>Mon, 27 Oct 2025 10:00:00 GMT</pubDate>
        </item>
        <item>
          <title>Guidance Standard: Kitchen Utensil Material Safety</title>
          <link>https://www.cpsc.gov/guidance/kitchen-standard</link>
          <description>Updated non-toxic coating standards for imported cookware.</description>
          <pubDate>Wed, 29 Oct 2025 14:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    items = parse_rss_feed_content(xml_sample, feed_name="CPSC Recalls")
    assert len(items) == 2
    assert items[0]["title"] == "Recall Notice: Stainless Steel Garlic Press Defect"
    assert items[0]["is_recall_or_hazard"] is True
    assert items[1]["is_recall_or_hazard"] is False


def test_fetch_regulatory_insights_envelope():
    res = fetch_regulatory_insights(category="Kitchen", use_mock_fallback=True)
    assert "envelope" in res
    assert res["envelope"]["source_type"] == "PUBLIC_NEWS"
    assert len(res["items"]) >= 1


# =====================================================================
# 3. Google Trends CSV Parser
# =====================================================================

def test_parse_google_trends_csv_rising_trend():
    csv_sample = """Category: All categories
Week,garlic press: (United States)
2025-08-03,40
2025-08-10,42
2025-08-17,41
2025-08-24,43
2025-08-31,65
2025-09-07,70
2025-09-14,75
2025-09-21,80
"""
    parsed = parse_google_trends_csv(csv_sample)
    assert parsed["envelope"]["source_type"] == "SELLER_INPUT"
    assert parsed["keyword"] == "garlic press"
    assert parsed["sample_points"] == 8
    assert parsed["trajectory"] == "RISING"
    assert parsed["momentum_pct_change"] > 10.0


def test_parse_google_trends_csv_invalid_format_raises():
    with pytest.raises(ValueError):
        parse_google_trends_csv("Invalid header without week column\nfoo,bar")


# =====================================================================
# 4. Brand Analytics Reports & Capability State
# =====================================================================

def test_parse_brand_analytics_search_terms_csv():
    csv_sample = """Department,Search Term,Search Frequency Rank,#1 Clicked ASIN,#1 Product Title,#1 Click Share,#1 Conversion Share
Kitchen,garlic press stainless steel,1420,B07XQXZXJC,Premium Garlic Press Pro,18.5%,22.1%
Kitchen,garlic mincer,4590,B08Y222222,Heavy Duty Garlic Crusher,12.0%,15.4%
Kitchen,silicone garlic peeler,18920,B09Z333333,Silicone Peeler Tube,25.0%,28.0%
"""
    res = parse_brand_analytics_search_terms(csv_sample, source_type=ProvenanceEnvelope.SELLER_INPUT)
    assert res["envelope"]["source_type"] == "SELLER_INPUT"
    terms = res["search_terms"]
    assert len(terms) == 3
    # Sorted by SFR ascending (1420 < 4590 < 18920)
    assert terms[0]["search_term"] == "garlic press stainless steel"
    assert terms[0]["search_frequency_rank"] == 1420
    assert len(terms[0]["top_clicked_asins"]) == 1
    assert terms[0]["top_clicked_asins"][0]["asin"] == "B07XQXZXJC"


def test_parse_search_query_performance():
    payload = {
        "queries": [
            {
                "search_query": "garlic press",
                "impressions": 125000,
                "clicks": 4200,
                "cart_adds": 850,
                "purchases": 320,
                "brand_share_pct": 8.5,
            }
        ]
    }
    res = parse_search_query_performance(payload)
    assert res["envelope"]["source_type"] == "AMAZON_OFFICIAL"
    assert res["queries_count"] == 1
    assert res["queries"][0]["purchases"] == 320


def test_brand_analytics_status_unverified():
    status = get_brand_analytics_status()
    # In default/demo mode without explicit Brand Registry role, must report NEEDS_BRAND_REGISTRY or NOT_AUTHORISED
    assert status["can_access_api"] is False
    assert status["supports_csv_import"] is True
    assert status["status"] in ("NEEDS_BRAND_REGISTRY", "NOT_AUTHORISED")


# =====================================================================
# 5. 6-Dimension Opportunity Scoring Engine
# =====================================================================

def test_opportunity_evaluator_go_verdict():
    costs = {
        "cogs": 5.0,
        "referral_fee_pct": 0.15,
        "fulfillment_fee": 3.0,
        "other_cost": 0.5,
        "target_margin_pct": 0.20,  # Requires $13.08
    }
    # Market price is $24.99 (plenty of margin), low competitors (3), low reviews (120), rising demand
    scorecard = evaluate_product_opportunity(
        product_id="OPP01",
        product_name="Innovative Citrus Peeler",
        cost_inputs=costs,
        market_median_price=24.99,
        competitor_count=3,
        top_competitor_reviews=120,
        moq=500,
        demand_trajectory="RISING",
        search_frequency_rank=8500,
        is_seasonal=False,
        is_hazmat_or_gated=False,
    )
    assert scorecard.verdict == OpportunityVerdict.GO
    assert scorecard.total_score >= 75.0
    assert "margin_feasibility" in scorecard.dimensions
    assert scorecard.dimensions["margin_feasibility"].score == 25.0


def test_opportunity_evaluator_margin_floor_breach_forces_no_go():
    costs = {
        "cogs": 10.0,
        "referral_fee_pct": 0.15,
        "fulfillment_fee": 4.0,
        "other_cost": 1.0,
        "target_margin_pct": 0.25,  # Requires $25.00
    }
    # Market median is $18.00 (below our target margin of $25.00)
    scorecard = evaluate_product_opportunity(
        product_id="OPP02",
        product_name="Cheap Generic Item",
        cost_inputs=costs,
        market_median_price=18.00,
        competitor_count=15,
        demand_trajectory="STABLE",
    )
    # INVIOLABLE FLOOR BREACH: Margin score must be 0 and verdict MUST be NO_GO
    assert scorecard.verdict == OpportunityVerdict.NO_GO
    assert scorecard.dimensions["margin_feasibility"].score == 0.0
    assert any("Margin floor breach" in r for r in scorecard.risks)


def test_opportunity_evaluator_missing_costs_insufficient_evidence():
    scorecard = evaluate_product_opportunity(
        product_id="OPP03",
        product_name="Unknown Cost Item",
        cost_inputs=None,
        market_median_price=20.00,
    )
    assert scorecard.verdict == OpportunityVerdict.INSUFFICIENT_EVIDENCE
    assert scorecard.total_score == 0.0


# =====================================================================
# 6. Market Radar & Opportunity API Endpoints
# =====================================================================

def test_api_market_radar_news():
    resp = client.get("/api/v1/market-radar/news?query=coffee+maker&max_records=5&mock=true")
    assert resp.status_code == 200
    data = resp.json()
    assert "articles" in data
    assert len(data["articles"]) > 0


def test_api_market_radar_regulatory():
    resp = client.get("/api/v1/market-radar/regulatory?category=Electronics")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) > 0


def test_api_market_radar_trends_upload_text():
    trends_csv = """Week,garlic press: (Worldwide)\n2025-09-01,50\n2025-09-08,55\n2025-09-15,60\n2025-09-22,65\n"""
    resp = client.post("/api/v1/market-radar/trends/upload", json={"csv_text": trends_csv})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_points"] == 4
    assert data["keyword"] == "garlic press"


def test_api_market_radar_brand_analytics_status():
    resp = client.get("/api/v1/market-radar/brand-analytics/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "supports_csv_import" in data


def test_api_market_radar_brand_analytics_upload_text():
    ba_csv = """Department,Search Term,Search Frequency Rank,#1 Clicked ASIN,#1 Product Title,#1 Click Share,#1 Conversion Share\nKitchen,garlic press,1200,B07XQXZXJC,Garlic Press,20.0%,25.0%\n"""
    resp = client.post("/api/v1/market-radar/brand-analytics/upload", json={"csv_text": ba_csv})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_terms"] == 1
    assert data["search_terms"][0]["search_term"] == "garlic press"


def test_api_opportunities_list_and_detail():
    # 1. List opportunities across catalog
    resp = client.get("/api/v1/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_evaluated" in data
    opps = data["opportunities"]
    assert len(opps) > 0

    first_pid = opps[0]["product_id"]

    # 2. Detail scorecard
    detail_resp = client.get(f"/api/v1/opportunities/{first_pid}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["product_id"] == first_pid
    assert "verdict" in detail
    assert "dimensions" in detail
    assert "margin_feasibility" in detail["dimensions"]
