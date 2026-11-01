"""
opportunity_evaluator.py — 6-Dimension Opportunity Scoring Engine for CommerceSense AI v3.

Evaluates product opportunities and catalog expansions across 6 rigorous dimensions:
  1. Demand & Search Momentum (25 pts)
  2. Competition Density & Moat (20 pts)
  3. Margin & Fee Feasibility (25 pts) — Inviolable Floor: 0 pts if market price < target margin
  4. Capital & MOQ Requirements (10 pts)
  5. Seasonality & Volatility (10 pts)
  6. Policy & Regulatory Risk (10 pts)

Outputs transparent verdict:
  - GO (>= 75 pts)
  - CONDITIONAL_GO (55 - 74 pts)
  - NO_GO (< 55 pts or margin floor breach)
  - INSUFFICIENT_EVIDENCE (missing cost inputs or demand signals)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from intelligence.pricing_engine import (
    breakeven_price,
    contribution_margin,
    target_margin_price,
)


class OpportunityVerdict(str, Enum):
    GO = "GO"
    CONDITIONAL_GO = "CONDITIONAL_GO"
    NO_GO = "NO_GO"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class DimensionScore:
    name: str
    score: float
    max_score: float
    details: str
    drivers: List[str] = field(default_factory=list)


@dataclass
class OpportunityScorecard:
    product_id: str
    product_name: str
    total_score: float
    verdict: OpportunityVerdict
    dimensions: Dict[str, DimensionScore]
    primary_recommendation: str
    conditions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "total_score": round(self.total_score, 1),
            "verdict": self.verdict.value,
            "primary_recommendation": self.primary_recommendation,
            "conditions": self.conditions,
            "risks": self.risks,
            "dimensions": {
                k: {
                    "name": v.name,
                    "score": round(v.score, 1),
                    "max_score": v.max_score,
                    "percentage": round(v.score / v.max_score * 100.0, 1) if v.max_score > 0 else 0.0,
                    "details": v.details,
                    "drivers": v.drivers,
                }
                for k, v in self.dimensions.items()
            },
        }


def evaluate_product_opportunity(
    product_id: str,
    product_name: str,
    cost_inputs: Optional[Dict[str, Any]],
    market_median_price: Optional[float],
    competitor_count: int = 5,
    top_competitor_reviews: int = 150,
    top_competitor_rating: float = 4.2,
    moq: int = 500,
    demand_trajectory: str = "STABLE",  # RISING, STABLE, DECLINING, UNKNOWN
    search_frequency_rank: Optional[int] = None,
    is_seasonal: bool = False,
    is_hazmat_or_gated: bool = False,
) -> OpportunityScorecard:
    """Evaluates an opportunity using deterministic 6-dimension scoring."""
    dimensions: Dict[str, DimensionScore] = {}
    risks: List[str] = []
    conditions: List[str] = []

    # 1. Cost & Margin Feasibility Check
    if not cost_inputs or not cost_inputs.get("cogs"):
        return OpportunityScorecard(
            product_id=product_id,
            product_name=product_name,
            total_score=0.0,
            verdict=OpportunityVerdict.INSUFFICIENT_EVIDENCE,
            dimensions={},
            primary_recommendation="Insufficient cost data: Supplier COGS and Amazon fulfillment fees required.",
            risks=["Cannot calculate margin feasibility without verified landed cost."],
        )

    cogs = float(cost_inputs.get("cogs", 0.0))
    ref_fee = float(cost_inputs.get("referral_fee_pct", 0.15))
    fba = float(cost_inputs.get("fulfillment_fee", 3.50))
    other = float(cost_inputs.get("other_cost", 0.0))
    target_m = float(cost_inputs.get("target_margin_pct", 0.20))

    be_price = breakeven_price(cogs, ref_fee, fba, other)
    target_price = target_margin_price(cogs, ref_fee, fba, other, target_m)

    # -------------------------------------------------------------
    # Dimension 1: Margin & Fee Feasibility (25 pts max)
    # -------------------------------------------------------------
    margin_drivers = []
    margin_score = 0.0

    if market_median_price is not None and target_price is not None:
        if market_median_price < target_price:
            # INVIOLABLE FLOOR BREACH: 0 points!
            margin_score = 0.0
            margin_drivers.append(
                f"Market price (${market_median_price:.2f}) is below target margin price (${target_price:.2f}). "
                "Negative margin pressure makes entry unviable."
            )
            risks.append("Margin floor breach: Competitor market prices do not cover minimum viable economics.")
        else:
            cm = contribution_margin(market_median_price, cogs, ref_fee, fba, other)
            m_pct = cm["margin_pct"] or 0.0
            if m_pct >= 0.35:
                margin_score = 25.0
                margin_drivers.append(f"Outstanding contribution margin ({m_pct*100:.1f}%) at market median price.")
            elif m_pct >= 0.25:
                margin_score = 20.0
                margin_drivers.append(f"Strong contribution margin ({m_pct*100:.1f}%) satisfies target hurdle.")
            elif m_pct >= 0.18:
                margin_score = 14.0
                margin_drivers.append(f"Acceptable margin ({m_pct*100:.1f}%) above breakeven floor.")
            else:
                margin_score = 7.0
                margin_drivers.append(f"Thin margin ({m_pct*100:.1f}%); sensitive to ad spend inflation.")
    else:
        margin_score = 10.0
        margin_drivers.append("Estimated baseline margin modeled from standard category benchmarks.")

    dimensions["margin_feasibility"] = DimensionScore(
        name="Margin & Fee Feasibility",
        score=margin_score,
        max_score=25.0,
        details=f"Target price: ${target_price:.2f} vs Market: ${market_median_price:.2f}" if target_price and market_median_price else "Calculated from cost inputs",
        drivers=margin_drivers,
    )

    # -------------------------------------------------------------
    # Dimension 2: Demand & Search Momentum (25 pts max)
    # -------------------------------------------------------------
    demand_drivers = []
    demand_score = 0.0

    traj_upper = demand_trajectory.upper()
    if traj_upper == "RISING":
        demand_score += 15.0
        demand_drivers.append("Rising search and customer demand momentum (>10% period growth).")
    elif traj_upper == "STABLE":
        demand_score += 10.0
        demand_drivers.append("Consistent, stable historical search volume.")
    elif traj_upper == "DECLINING":
        demand_score += 4.0
        demand_drivers.append("Declining trend trajectory; customer interest waning.")
        risks.append("Declining demand velocity observed in search trends.")
    else:
        demand_score += 8.0
        demand_drivers.append("Uncertain demand velocity; based on baseline sales.")

    # Search Frequency Rank points
    if search_frequency_rank is not None:
        if search_frequency_rank < 10000:
            demand_score += 10.0
            demand_drivers.append(f"Top-tier Amazon search frequency rank (#{search_frequency_rank}).")
        elif search_frequency_rank < 50000:
            demand_score += 7.0
            demand_drivers.append(f"Solid Amazon search volume (SFR #{search_frequency_rank}).")
        else:
            demand_score += 4.0
            demand_drivers.append(f"Niche / long-tail search volume (SFR #{search_frequency_rank}).")
    else:
        demand_score += 5.0

    dimensions["demand_momentum"] = DimensionScore(
        name="Demand & Search Momentum",
        score=min(demand_score, 25.0),
        max_score=25.0,
        details=f"Trajectory: {demand_trajectory}",
        drivers=demand_drivers,
    )

    # -------------------------------------------------------------
    # Dimension 3: Competition Density & Moat (20 pts max)
    # -------------------------------------------------------------
    comp_drivers = []
    comp_score = 0.0

    if competitor_count <= 4:
        comp_score += 12.0
        comp_drivers.append(f"Low competitor density ({competitor_count} direct offers).")
    elif competitor_count <= 10:
        comp_score += 8.0
        comp_drivers.append(f"Moderate competitor count ({competitor_count} offers).")
    else:
        comp_score += 4.0
        comp_drivers.append(f"High competitor density ({competitor_count} active offers).")
        risks.append("Saturated competitor landscape; high PPC ad costs anticipated.")

    # Review barrier / moat
    if top_competitor_reviews < 300:
        comp_score += 8.0
        comp_drivers.append("Low review moat: Top competitor has <300 reviews; easy to overcome with quality product.")
    elif top_competitor_reviews < 1500:
        comp_score += 5.0
        comp_drivers.append(f"Moderate review barrier (~{top_competitor_reviews} reviews on incumbents).")
    else:
        comp_score += 2.0
        comp_drivers.append(f"Entrenched competitors with {top_competitor_reviews:,} reviews; requires differentiation.")
        risks.append(f"High review barrier: Incumbents hold {top_competitor_reviews:,} reviews.")

    dimensions["competition_moat"] = DimensionScore(
        name="Competition Density & Moat",
        score=min(comp_score, 20.0),
        max_score=20.0,
        details=f"{competitor_count} competitors, top reviews: {top_competitor_reviews}",
        drivers=comp_drivers,
    )

    # -------------------------------------------------------------
    # Dimension 4: Capital & MOQ Requirements (10 pts max)
    # -------------------------------------------------------------
    capital_drivers = []
    initial_cash = moq * cogs
    if initial_cash < 2500.0:
        cap_score = 10.0
        capital_drivers.append(f"Low initial capital outlay (${initial_cash:,.2f} for {moq} units).")
    elif initial_cash < 7500.0:
        cap_score = 7.0
        capital_drivers.append(f"Moderate working capital requirement (${initial_cash:,.2f}).")
    elif initial_cash < 15000.0:
        cap_score = 4.0
        capital_drivers.append(f"Significant initial capital needed (${initial_cash:,.2f}).")
        conditions.append(f"Ensure supplier MOQ ({moq} units) can be split or financed.")
    else:
        cap_score = 2.0
        capital_drivers.append(f"High capital barrier: ${initial_cash:,.2f} required for first PO.")
        risks.append(f"Substantial cash tie-up (${initial_cash:,.2f}) creates working capital risk.")

    dimensions["capital_moq"] = DimensionScore(
        name="Capital & MOQ",
        score=cap_score,
        max_score=10.0,
        details=f"MOQ: {moq} units, Initial Cash: ${initial_cash:,.2f}",
        drivers=capital_drivers,
    )

    # -------------------------------------------------------------
    # Dimension 5: Seasonality & Volatility (10 pts max)
    # -------------------------------------------------------------
    season_drivers = []
    if is_seasonal:
        season_score = 3.0
        season_drivers.append("High seasonal clustering; demand concentrated in narrow annual windows.")
        risks.append("Seasonality risk: Potential excess inventory if seasonal window closes early.")
        conditions.append("Align purchase order timing strictly with seasonal ramp-up.")
    else:
        season_score = 10.0
        season_drivers.append("Consistent year-round demand; low inventory obsolescence risk.")

    dimensions["seasonality"] = DimensionScore(
        name="Seasonality & Stability",
        score=season_score,
        max_score=10.0,
        details="Seasonal item" if is_seasonal else "Year-round demand",
        drivers=season_drivers,
    )

    # -------------------------------------------------------------
    # Dimension 6: Policy & Category Risk (10 pts max)
    # -------------------------------------------------------------
    risk_drivers = []
    if is_hazmat_or_gated:
        risk_score = 2.0
        risk_drivers.append("Restricted/gated category or hazmat compliance requirements.")
        risks.append("Policy risk: Amazon ungating approval and safety documentation required.")
        conditions.append("Obtain safety data sheets (SDS) and lab testing before shipping inventory.")
    else:
        risk_score = 10.0
        risk_drivers.append("Unrestricted open category; standard FBA acceptance.")

    dimensions["policy_risk"] = DimensionScore(
        name="Policy & Category Risk",
        score=risk_score,
        max_score=10.0,
        details="Gated / Special Compliance" if is_hazmat_or_gated else "Standard Category",
        drivers=risk_drivers,
    )

    # -------------------------------------------------------------
    # Aggregate Verdict
    # -------------------------------------------------------------
    total = sum(d.score for d in dimensions.values())

    # Hard Gate: If margin score is 0 due to margin floor breach, force NO_GO
    if margin_score == 0.0:
        verdict = OpportunityVerdict.NO_GO
        recom = "NO_GO: Market price is below the seller's minimum target margin floor. Do not launch without lower supplier pricing."
    elif total >= 75.0:
        verdict = OpportunityVerdict.GO
        recom = "GO: Strong profit potential, healthy demand trajectory, and manageable competitive moat."
    elif total >= 55.0:
        verdict = OpportunityVerdict.CONDITIONAL_GO
        recom = "CONDITIONAL_GO: Viable opportunity subject to specific operational conditions (differentiation, MOQ negotiation)."
    else:
        verdict = OpportunityVerdict.NO_GO
        recom = "NO_GO: High competition barrier or insufficient margin to cover customer acquisition costs."

    return OpportunityScorecard(
        product_id=product_id,
        product_name=product_name,
        total_score=total,
        verdict=verdict,
        dimensions=dimensions,
        primary_recommendation=recom,
        conditions=conditions,
        risks=risks,
    )

