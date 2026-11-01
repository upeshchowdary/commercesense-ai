# CommerceSense AI v3 — Forecasting & Inventory Methodology

> **Forecasting Methodology Document:** `docs/FORECASTING_METHODOLOGY.md`  
> **Status:** Canonical Mathematical Specification  
> **Target Version:** CommerceSense AI v3  

---

## 1. Challenges of Amazon Demand Forecasting

Forecasting e-commerce demand on Amazon presents distinct mathematical challenges that render simple moving averages or standard linear regressions inaccurate:

1. **Stockout Censorship (The Zero-Demand Illusion):** When a product runs out of stock, observed sales drop to zero. If this zero is treated as true customer demand, historical velocity is artificially depressed, leading to under-ordering and repeat stockouts.
2. **Intermittent / Lumpy Demand:** Slow-moving or high-ticket SKUs frequently experience runs of zero-sales days punctuated by sporadic multi-unit purchases, violating Gaussian error assumptions.
3. **Day-of-Week Seasonality:** E-commerce exhibits strong weekly cycles (e.g. weekend surges or mid-week office purchasing).
4. **Supply Chain Lead Time Variance:** Inward shipments to Amazon FBA fulfillment centers suffer from transit delays, customs holds, and warehouse check-in backlogs.

---

## 2. Stockout-Censored Demand Adjustment (Uncensoring)

Before any time-series model is trained, the historical daily sales series $\{y_t\}_{t=1}^T$ must be **un-censored** to reconstruct latent customer demand $\{\hat{d}_t\}_{t=1}^T$.

```
+==================================================================================================+
|                               STOCKOUT DEMAND ADJUSTMENT PIPELINE                                |
+==================================================================================================+

   Observed Daily Sales (y_t)  +  Inventory Level (I_t)
               |
               v
   +-------------------------------------------------------+
   | Condition Check: Is I_t == 0 (or stockout occurred)?  |
   +---------------------------+---------------------------+
                               |
            +------------------+------------------+
            | NO (In-Stock)                       | YES (Stocked Out)
            v                                     v
   +-----------------------+             +-----------------------------------------+
   | Latent Demand:        |             | Latent Demand Imputation:               |
   |   d_t = y_t           |             |   d_t = Moving_Median(d_{in-stock}, 14) |
   | (Uncensored observed) |             |   Flag: "STOCKOUT_IMPUTED"              |
   +-----------------------+             +-----------------------------------------+
```

### Uncensoring Algorithm
For each day $t \in [1, T]$ with inventory $I_t$ and sales $y_t$:

$$\hat{d}_t = \begin{cases} y_t, & \text{if } I_t > 0 \\ \text{Median}\left( \{ y_\tau \mid I_\tau > 0, \; \tau \in [t-14, t+14] \} \right), & \text{if } I_t = 0 \end{cases}$$

If an extended stockout exceeds 28 days, imputation uses the pre-stockout 14-day weighted moving average. This ensures forecasting models predict true underlying demand rather than warehouse availability.

---

## 3. Forecasting Algorithms via StatsForecast

CommerceSense AI v3 integrates Nixtla's **StatsForecast** library, utilizing fast, C/Numba-compiled statistical models:

```
+---------------------------------------------------------------------------+
|                       STATISTICAL MODEL CANDIDATES                        |
+-------------------+-------------------------------------------------------+
| MODEL             | APPLICABILITY & RATIONALE                             |
+-------------------+-------------------------------------------------------+
| AutoARIMA         | High-velocity, stable products with clear trend and   |
|                   | day-of-week seasonality (7-day period).               |
+-------------------+-------------------------------------------------------+
| Croston's Method  | Intermittent demand items with sporadic non-zero sales.|
|                   | Decomposes demand into magnitude and inter-arrival.   |
+-------------------+-------------------------------------------------------+
| SBA               | Syntetos-Boylan Approximation: debiased Croston       |
|                   | variant recommended for lumpy spare-parts / slow SKUs.|
+-------------------+-------------------------------------------------------+
| Seasonal Naive    | Deterministic benchmark: $d_t = d_{t-7}$.             |
+-------------------+-------------------------------------------------------+
| Historic Average  | Flat baseline benchmark for minimum-variance control. |
+-------------------+-------------------------------------------------------+
```

### 3.1 Croston's Method Formulation
Croston separates intermittent time series into two independent sequences:
1. Demand size $z_k$ when demand occurs ($y_t > 0$).
2. Inter-arrival time $p_k$ between positive demand periods.

Both components are updated via exponential smoothing parameter $\alpha \in (0, 1)$:

$$\hat{z}_{k+1} = \hat{z}_k + \alpha (z_k - \hat{z}_k)$$

$$\hat{p}_{k+1} = \hat{p}_k + \alpha (p_k - \hat{p}_k)$$

The forecast demand rate per period is:

$$\hat{y}_{\text{Croston}} = \frac{\hat{z}_{k+1}}{\hat{p}_{k+1}}$$

### 3.2 Syntetos-Boylan Approximation (SBA)
Because Croston's ratio estimator has a known positive bias, SBA applies a correction factor:

$$\hat{y}_{\text{SBA}} = \left( 1 - \frac{\alpha}{2} \right) \frac{\hat{z}_{k+1}}{\hat{p}_{k+1}}$$

### 3.3 Prediction Intervals
Forecasts generate 80% and 95% confidence intervals $[L_{\alpha}, U_{\alpha}]$ to inform conservative vs. aggressive replenishment policies.

---

## 4. Inventory Parameters & Reorder Mathematics

```
+==================================================================================================+
|                                  INVENTORY REORDER MECHANICS                                     |
+==================================================================================================+

   Current Stock (I)
         |
         |  (Daily Demand Burn)
         v
   +-----------------------+
   | Reorder Point (ROP)   | ======> Trigger Purchase Order of Suggested Quantity (Q_order)
   +-----------------------+
         |
         |  (Burn during Lead Time L)
         v
   +-----------------------+
   | Safety Stock (SS)     | ======> Buffer protecting against lead time & demand variance
   +-----------------------+
         |
         v
       ZERO (Stockout threshold)
```

### 4.1 Daily Demand Aggregation ($D_{\text{weighted}}$)
When evaluating short-term cover, recent velocity is weighted more heavily than distant history:

$$D_{\text{weighted}} = \frac{3 \cdot \sum_{t=1}^7 d_t + 2 \cdot \sum_{t=8}^{14} d_t + 1 \cdot \sum_{t=15}^{30} d_t}{3 \cdot 7 + 2 \cdot 7 + 1 \cdot 16} = \frac{3 \cdot \text{Total}_{7\text{d}} + 2 \cdot \text{Total}_{14\text{d}} + 1 \cdot \text{Total}_{30\text{d}}}{51}$$

### 4.2 Days of Cover ($DOC$)
$$DOC = \begin{cases} \frac{I_{\text{current}}}{D_{\text{weighted}}}, & \text{if } D_{\text{weighted}} > 0 \\ \text{None (Zero Demand)}, & \text{if } D_{\text{weighted}} = 0 \end{cases}$$

### 4.3 Dynamic Safety Stock ($SS$)
Accounting for uncertainty in both customer demand ($\sigma_D$) and supplier lead time ($\sigma_L$):

$$SS = Z \times \sqrt{L \times \sigma_D^2 + D_{\text{avg}}^2 \times \sigma_L^2}$$

Where:
- $Z$: Normal distribution service factor ($Z = 1.645$ for 95% service level; $Z = 2.326$ for 99%).
- $L$: Nominal lead time in days.
- $\sigma_D$: Standard deviation of daily demand.
- $\sigma_L$: Standard deviation of supplier lead time in days.

If lead time is constant ($\sigma_L = 0$):

$$SS = Z \times \sigma_D \times \sqrt{L}$$

### 4.4 Reorder Point ($ROP$)
The inventory level that triggers a replenishment order:

$$ROP = (D_{\text{weighted}} \times L) + SS$$

### 4.5 Suggested Reorder Quantity ($Q_{\text{order}}$)
To reach a target stock cover (default: 45 days) while honoring Minimum Order Quantities ($MOQ$) and Supplier Batch Multiples ($M_{\text{batch}}$):

$$Q_{\text{target}} = \max\left(0, \; (D_{\text{weighted}} \times T_{\text{target\_days}}) - I_{\text{current}} - I_{\text{inbound}}\right)$$

$$Q_{\text{moq}} = \begin{cases} \max(Q_{\text{target}}, \; MOQ), & \text{if } Q_{\text{target}} > 0 \text{ and } MOQ \text{ set} \\ Q_{\text{target}}, & \text{otherwise} \end{cases}$$

$$Q_{\text{order}} = \begin{cases} \left\lceil \frac{Q_{\text{moq}}}{M_{\text{batch}}} \right\rceil \times M_{\text{batch}}, & \text{if } Q_{\text{moq}} > 0 \text{ and } M_{\text{batch}} \text{ set} \\ Q_{\text{moq}}, & \text{otherwise} \end{cases}$$

---

## 5. What-If Simulation Scenarios

In the **Product Workspace (Inventory Tab)**, operators test supply chain shocks:
1. **Lead Time Spike Scenario:** Simulates supplier delay ($L \to 1.5 \times L$), projecting whether current inventory will stock out before arrival.
2. **Demand Uplift Scenario:** Simulates promotional surge ($D \to 1.25 \times D$), recalculating revised days of cover and stockout date.
3. **Inbound Shipment Simulation:** Incorporates a known purchase order ($Q_{\text{inbound}}$ arriving at day $t_{\text{arrival}}$), displaying the projected 60-day stock trajectory chart.

