# CommerceSense AI v3 — Pricing Methodology & Mathematics

> **Pricing Methodology Document:** `docs/PRICING_METHODOLOGY.md`  
> **Status:** Canonical Mathematical Specification  
> **Target Version:** CommerceSense AI v3  

---

## 1. Principles of Constrained E-Commerce Pricing

CommerceSense AI v3 implements **Constrained Value Pricing**, explicitly rejecting the naive "race to the bottom" repricing algorithms common in legacy Amazon software. 

Key Foundational Axioms:
1. **Mathematical Precision Over Floating-Point Approximation:** Standard IEEE 754 floating-point numbers (`float`) introduce binary representation errors that corrupt financial rounding. All pricing math is executed strictly using Python's `decimal.Decimal` with fixed-point rounding (`ROUND_HALF_UP`) and persisted in SQL as `DECIMAL(12, 4)` and `DECIMAL(10, 2)`.
2. **Cost-Completeness:** Amazon sellers do not merely pay referral fees; their true variable costs include FBA fulfillment fees, Amazon closing fees (tiered by price bracket), inward freight, packaging, returns allowances, and attributed unit ad spend. A price recommendation that ignores any of these components is functionally hazardous.
3. **Strict Margin Floor Protection:** The system enforces an inviolable lower bound (`Margin Floor`). An automated or suggested price will **never** recommend dropping below the seller's configured target margin price, regardless of what competitors charge.
4. **Context-Aware Matching:** Not all competitors are equal. A price must be compared within a structured 3-tier taxonomy (Same ASIN, Exact Equivalent, Substitute) rather than a blunt category median.

---

## 2. Cost-Complete Mathematical Formulations

```
+==================================================================================================+
|                                UNIT ECONOMICS DECOMPOSITION                                      |
+==================================================================================================+

   SELLING PRICE (P)
   +--------------------------------------------------------------------------------------------+
   |  CONTRIBUTION MARGIN (CM)   |                    TOTAL VARIABLE COSTS (VC)                 |
   |                             | COGS + FBA + Closing + Packaging + AdSpend + ReferralFee(P)  |
   +-----------------------------+--------------------------------------------------------------+
```

### 2.1 Variable Definitions
- $P \in \mathbb{R}^+$: Proposed or Current Selling Price (in local currency, e.g. INR or USD).
- $C_{\text{cogs}} \ge 0$: Cost of Goods Sold per unit.
- $F_{\text{fba}} \ge 0$: FBA Fulfillment Fee (pick, pack, and weight handling).
- $F_{\text{close}}(P) \ge 0$: Amazon Closing Fee (variable by price tier).
- $C_{\text{pack}} \ge 0$: Packaging, prep, and inward freight cost per unit.
- $C_{\text{other}} \ge 0$: Other direct variable costs (returns allowance, damage provision).
- $C_{\text{ad}} \ge 0$: Attributed advertising spend per unit ($\text{Total Ad Spend} / \text{Total Units Sold}$).
- $r_{\text{ref}} \in [0, 1)$: Amazon Category Referral Fee percentage (e.g. $0.1500$ for 15%).
- $m_{\text{target}} \in [0, 1)$: Seller's Target Contribution Margin percentage (e.g. $0.2000$ for 20%).

### 2.2 Total Variable Cost Function ($VC(P)$)
The total variable cost per unit is composed of fixed unit expenses plus price-dependent Amazon fees:

$$C_{\text{fixed\_unit}} = C_{\text{cogs}} + F_{\text{fba}} + F_{\text{close}}(P) + C_{\text{pack}} + C_{\text{other}} + C_{\text{ad}}$$

$$\text{Referral Fee}(P) = P \times r_{\text{ref}}$$

$$VC(P) = C_{\text{fixed\_unit}} + (P \times r_{\text{ref}})$$

### 2.3 Contribution Margin ($CM$) & Margin Percentage ($M\%$)
The contribution margin is the net cash contribution each sold unit delivers toward covering fixed business overhead and net profit:

$$CM(P) = P - VC(P) = P \times (1 - r_{\text{ref}}) - C_{\text{fixed\_unit}}$$

$$M\%(P) = \begin{cases} \frac{CM(P)}{P} = (1 - r_{\text{ref}}) - \frac{C_{\text{fixed\_unit}}}{P}, & \text{if } P > 0 \\ 0, & \text{if } P = 0 \end{cases}$$

### 2.4 Breakeven Price ($P_{\text{be}}$)
The Breakeven Price is the exact selling price at which the contribution margin is zero ($CM(P_{\text{be}}) = 0$):

$$0 = P_{\text{be}} \times (1 - r_{\text{ref}}) - C_{\text{fixed\_unit}}$$

$$P_{\text{be}} = \frac{C_{\text{fixed\_unit}}}{1 - r_{\text{ref}}}$$

*Precondition:* $1 - r_{\text{ref}} > 0$. If $r_{\text{ref}} \ge 1.0$, breakeven is mathematically impossible.

### 2.5 Target Margin Price ($P_{\text{target}}$)
The Target Margin Price is the exact selling price that yields the seller's desired target margin percentage ($M\%(P) = m_{\text{target}}$):

$$m_{\text{target}} = \frac{P_{\text{target}} \times (1 - r_{\text{ref}}) - C_{\text{fixed\_unit}}}{P_{\text{target}}}$$

$$P_{\text{target}} \times m_{\text{target}} = P_{\text{target}} \times (1 - r_{\text{ref}}) - C_{\text{fixed\_unit}}$$

$$P_{\text{target}} \times (1 - r_{\text{ref}} - m_{\text{target}}) = C_{\text{fixed\_unit}}$$

$$P_{\text{target}} = \frac{C_{\text{fixed\_unit}}}{1 - r_{\text{ref}} - m_{\text{target}}}$$

*Mathematical Guardrail:* If $1 - r_{\text{ref}} - m_{\text{target}} \le 0$, the target margin is mathematically unreachable given the fee structure. The engine must return `None` (or flag `TARGET_UNREACHABLE`), rather than generating a negative or infinite price.

---

## 3. The 3-Tier Competitor Matching Taxonomy

Competitors are evaluated through a rigorous 3-tier hierarchy:

```
+===========================================================================+
|                      COMPETITOR MATCHING TAXONOMY                         |
+===========================================================================+

  TIER 1: SAME ASIN (DIRECT BUY BOX COMPETITION)
  • Identical product listing shared by multiple sellers.
  • Dynamics: Direct Buy Box rotation based on landed price, fulfillment (FBA),
    and seller defect rate.
  • Action: High sensitivity. Match or win Buy Box if $P_{\text{bb}} \ge P_{\text{target}}$.

  TIER 2: EXACT EQUIVALENT (DIRECT SPEC EQUIVALENT)
  • Different ASIN, but identical brand/spec/form factor (e.g. 100ml vs 100ml).
  • Dynamics: Customer substitutes directly based on price, review score, and badge.
  • Action: Maintain price parity within [-5%, +10%] bracket of verified median.

  TIER 3: CATEGORY SUBSTITUTE (FUNCTIONAL ALTERNATIVE)
  • Different brand, differing specifications or material (e.g. silicone vs steel).
  • Dynamics: Macro market reference. Elasticity influenced by product differentiation.
  • Action: Loose tracking. Never force price matching against lower-tier substitutes.
```

---

## 4. Contradiction & Spread Handling

When observing competitor prices from multiple sources or across disparate sellers, the pricing engine computes the **Relative Price Spread ($S_{\text{rel}}$)**:

$$S_{\text{rel}} = \frac{P_{\text{max}} - P_{\text{min}}}{P_{\text{median}}}$$

### Confidence Downgrade Rules:
1. If $S_{\text{rel}} > 0.15$ (price dispersion exceeds 15% of the median):
   - Downgrade recommendation confidence to `low`.
   - Append an explicit reasoning statement: `"High competitor price dispersion (X% spread); median price may not reflect true market equilibrium."`
2. If sample size $N < 3$:
   - Set confidence to `low` or `insufficient_data`.
3. If $S_{\text{rel}} \le 0.15$ and $N \ge 3$:
   - Retain `high` or `medium` confidence.

---

## 5. DO_NOT_MATCH Rules & Floor Enforcement

The pricing engine is bound by safety rules that override any competitive recommendation:

```
+---------------------------------------------------------------------------+
|                          DO_NOT_MATCH GUARDRAILS                          |
+---------------------------------------------------------------------------+
| RULE 1: INVIOLABLE MARGIN FLOOR                                           |
|   IF Competitor_Price < P_target THEN                                     |
|     DO NOT MATCH. Recommend P_target as absolute lower bound.             |
|     Flag: "BELOW_MARGIN_FLOOR - Competitor price breaches viability."     |
+---------------------------------------------------------------------------+
| RULE 2: REPUTATION ASYMMETRY                                              |
|   IF Our_Rating >= 4.3 AND Competitor_Rating <= 3.7 THEN                  |
|     DO NOT MATCH. Retain premium pricing (premium justified by quality).  |
|     Flag: "PREMIUM_JUSTIFIED - Superior review rating defends price."     |
+---------------------------------------------------------------------------+
| RULE 3: INVENTORY SHORTAGE SUPPRESSION                                    |
|   IF Days_Of_Cover < 14 THEN                                              |
|     DO NOT DROP PRICE. Raising or holding price slows velocity and        |
|     prevents costly stockout penalties.                                   |
|     Flag: "STOCKOUT_PRESERVATION - Holding price to ration inventory."    |
+---------------------------------------------------------------------------+
| RULE 4: UNVERIFIED SELLER SUPPRESSION                                     |
|   IF Competitor offer is non-Prime / merchant-fulfilled with >14d delivery|
|     DO NOT MATCH. FBA convenience justifies price premium over FBM.       |
+---------------------------------------------------------------------------+
```

---

## 6. What-If Scenario Analysis at Current Volume

When operators simulate price changes in the **Pricing Lab**, the engine models financial impact under the conservative assumption of **Zero Elasticity ($\Delta Q = 0$)** as the baseline, followed by parameterized sensitivity curves:

$$\Delta \text{Revenue} = (\Delta P) \times Q_{\text{current}}$$

$$\Delta \text{Contribution Margin} = \left[ CM(P_{\text{new}}) - CM(P_{\text{current}}) \right] \times Q_{\text{current}}$$

By displaying the exact delta in contribution dollars at current sales volume, the operator can see immediately that dropping a price by \$1.50 to chase Buy Box share requires selling 28% more units just to break even on gross profit.

