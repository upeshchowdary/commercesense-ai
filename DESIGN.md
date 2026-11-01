# CommerceSense AI v3 — Design System & UI/UX Specification

> **Design Specification Document:** `DESIGN.md`  
> **Status:** Canonical UI/UX Specification  
> **Art Direction:** "The Seller Control Room"  
> **Target Version:** CommerceSense AI v3  

---

## 1. Art Direction & Philosophy: "The Seller Control Room"

**CommerceSense AI v3** abandons the dark-neon aesthetic typical of developer hobby projects in favor of **"The Seller Control Room"**: a calm, authoritative, high-trust B2B SaaS interface tailored for serious e-commerce operators, brand owners, and financial controllers.

```
+==================================================================================================+
|                                    ART DIRECTION PRINCIPLES                                      |
+==================================================================================================+
| 1. LIGHT-FIRST DEFAULT: Clean, daylight-readable, high-contrast canvas with dark mode support.    |
| 2. CALM FOREST & SAGE ACCENTS: Restrained, sophisticated greens reflecting sustainable profit,    |
|    cash flow, and organic growth, replacing garish purple gradients and neon cyan glows.         |
| 3. HIGH DATA DENSITY: Optimized for maximum information per square inch. Crisp numbers, compact  |
|    tabular rows, small badges, and informative tooltips over oversized empty white-space.         |
| 4. RIGOROUS PROVENANCE BADGING: Every data point communicates its origin. Visual trust is built   |
|    on transparent source attribution.                                                            |
| 5. DECISION SUPPORT OVER AUTOMATION: Structured "Why Panels" and audit queues ensure the operator|
|    always understands the mathematical and evidentiary basis before taking action.               |
+==================================================================================================+
```

---

## 2. Color Palette & Design Tokens

### 2.1 Surfaces & Canvas (Light-First Primary, Dark Support)

| Token Name | Light Value (Hex) | Dark Value (Hex) | Purpose |
|:---|:---|:---|:---|
| `canvas-bg` | `#F9FAF9` (Off-White / Alabaster) | `#0B0F0E` (Deep Charcoal) | Application root background |
| `surface-card` | `#FFFFFF` (Pure White) | `#131A18` (Dark Surface) | Primary card and table container |
| `surface-subtle`| `#F3F4F6` (Muted Gray) | `#1C2623` (Muted Dark) | Table headers, secondary panels |
| `surface-hover` | `#E5E7EB` (Subtle Hover) | `#263632` (Dark Hover) | Interactive row hover |
| `border-card` | `#E5E7EB` (Hairline Gray) | `#263632` (Hairline Dark) | Card and cell borders |
| `border-focus` | `#1B4332` (Forest Green) | `#52B788` (Sage Green) | Accessible focus rings |

### 2.2 Brand & Accents (The Forest & Sage Spectrum)

| Token Name | Hex Value | Role & Usage |
|:---|:---|:---|
| `forest-deep` | `#1B4332` | Primary brand color, primary CTA buttons, active sidebar items |
| `forest-mid` | `#2D6A4F` | Secondary buttons, chart primary series, table accents |
| `sage-accent` | `#52B788` | Focus states, positive KPI trends, Buy Box owner badges |
| `sage-subtle` | `#D8F3DC` | Sage badge background, alert success background |
| `text-primary`| `#111827` (Light) / `#F9FAF9` (Dark) | Primary headers, numeric metrics, bold table text |
| `text-muted` | `#4B5563` (Light) / `#9CA3AF` (Dark) | Secondary descriptions, timestamps, table column headers |

### 2.3 Status & Severity Palette

| Status / Severity | Foreground (Text/Icon) | Background (Badge/Card) | Border |
|:---|:---|:---|:---|
| **High Risk / Critical** | `#DC2626` (Crimson Red) | `#FEF2F2` (Soft Rose) | `#FCA5A5` |
| **Medium Risk / Warning** | `#D97706` (Amber Ochre) | `#FFFBEB` (Soft Sand) | `#FCD34D` |
| **Low Risk / Info** | `#2563EB` (Cobalt Blue) | `#EFF6FF` (Soft Sky) | `#93C5FD` |
| **Healthy / Positive** | `#16A34A` (Emerald Green) | `#F0FDF4` (Soft Mint) | `#86EFAC` |
| **Neutral / Inactive** | `#6B7280` (Cool Gray) | `#F3F4F6` (Subtle Slate)| `#D1D5DB` |

---

## 3. Provenance Badge System

Every table, metric card, and modal header renders a standardized **Provenance Badge** (8px vertical alignment, 11px font size, uppercase tracking):

```
+-------------------------------------------------------------------------------+
|                         PROVENANCE BADGE SPECIFICATIONS                       |
+-------------------+-----------------------+-------------------+---------------+
| BADGE LABEL       | BG TOKEN              | TEXT TOKEN        | ICON (Lucide) |
+-------------------+-----------------------+-------------------+---------------+
| AMAZON_OFFICIAL   | #1B4332 (Solid)       | #FFFFFF (White)   | ShieldCheck   |
| PUBLIC_NEWS       | #E0F2FE (Light Cyan)  | #0369A1 (Cyan)    | Globe         |
| SELLER_INPUT      | #F1F5F9 (Slate Light) | #334155 (Slate)   | FileSpreadsheet|
| CALCULATED        | #EFF6FF (Blue Light)  | #1D4ED8 (Blue)    | Calculator    |
| MODELLED          | #F3E8FF (Purple Light)| #6B21A8 (Purple)  | Cpu           |
| CACHED            | #FEF3C7 (Amber Light) | #B45309 (Amber)   | Clock         |
| DEMO              | #F3F4F6 (Dotted Gray) | #4B5563 (Gray)    | TestTube      |
| MISSING           | #FEE2E2 (Rose Light)  | #B91C1C (Rose)    | AlertCircle   |
+-------------------+-----------------------+-------------------+---------------+
```

---

## 4. Layout Architecture & Navigation Grid

### 4.1 Global Viewport Anatomy (Desktop 1440px)
```
+--------------------------------------------------------------------------------------------------+
| TOPBAR (Height: 56px)                                                                            |
| [Logo: CommerceSense AI] [Global Search / Command Palette (Ctrl+K)] [Mode: FREE_ONLY] [Theme] [User] |
+---------------+----------------------------------------------------------------------------------+
| SIDEBAR       | MAIN CONTENT WORKSPACE                                                           |
| (Width: 220px)| (Padding: 24px, Max Width: 1600px, Margin: 0 Auto)                               |
|               |                                                                                  |
| • Overview    | [Header: Page Title + Provenance Status Indicator + Primary Action]             |
| • Portfolio   |                                                                                  |
| • Workspace   | [KPI Metric Strip (4 to 5 compact tiles)]                                        |
| • Competitors |                                                                                  |
| • Market Radar| [Main Grid Area: Split 65% Primary Data Table / 35% Inspector & Charts]          |
| • Opportunity |                                                                                  |
| • Pricing Lab | [Secondary Drawer / Expandable Why Panel]                                        |
| • Action Center                                                                                  |
| • Automations |                                                                                  |
| • Reports     |                                                                                  |
| • Settings    |                                                                                  |
+---------------+----------------------------------------------------------------------------------+
```

---

## 5. Route-by-Route UX Specifications

### Route 01: Overview (`/overview`)
- **Header:** "Executive Control Room" + Status indicator (`FREE_ONLY: Active`).
- **KPI Metric Strip (5 Columns):**
  1. *30d Revenue:* Currency total (`AMAZON_OFFICIAL` / `DEMO`).
  2. *Blended Margin:* % (`CALCULATED`).
  3. *Total Attention Score:* Aggregate risk index (0–100) (`CALCULATED`).
  4. *Stockout Risk:* Count of SKUs with DOC < 10 days (`CALCULATED`).
  5. *Wasted PPC Spend:* Dollars at risk on zero-sale campaigns (`CALCULATED`).
- **Main Section:**
  - Left (60%): **This Week's Attention Leaderboard** (ranked table showing SKU, Name, Top Issue, Dollars at Risk, Action Button).
  - Right (40%): **Portfolio Risk Matrix** (Scatter plot: Margin % on X-axis vs. Days of Cover on Y-axis).

### Route 02: Product Portfolio (`/portfolio`)
- **Header:** "Product Portfolio" + Search input + Filter pills (`All`, `Stockout Risk`, `Below Floor`, `Emerging Issue`).
- **Master Operational Table:**
  - Columns: `SKU / ASIN`, `Product Title`, `Category`, `Price`, `Margin %`, `Days of Cover`, `Rating (Stars)`, `Attention Score`, `Provenance`, `Actions`.
  - Row Expansion: Clicking row opens quick inline summary drawer.

### Route 03: Product Workspace (`/products/:id`)
- **Header:** SKU Title, Category, ASIN, Active Attention Score Badge (e.g. `84 / 100 - High Risk`).
- **7-Tab Workspace:**
  1. `Overview`: 60-day historical chart (Daily Sales, Inventory, Rank, Buy Box ownership).
  2. `Listing`: 0–100 Listing Health Score breakdown, rule audit checklist, AI rewrite proposal with numbers-grounding guardrail.
  3. `Pricing`: Unit economics card (COGS, referral, fulfillment, closing), Breakeven vs Target Margin Price, Competitor spread histogram, What-if price simulator.
  4. `Reviews`: Rating distribution bar chart, 7/30/90-day velocity, deterministic keyword themes with verbatim quotes, emerging issue spike detector.
  5. `Inventory`: Daily demand weighted, Days of cover, Dynamic safety stock, Reorder point, 60-day inventory burn chart with inbound shipment scenario.
  6. `Competitors`: 3-tier competitor comparison table (Tier 1 Buy Box, Tier 2 Equivalent, Tier 3 Substitute), Buy Box share tracker.
  7. `Forecast`: StatsForecast demand trajectory (AutoARIMA, Croston), stockout-censored historical comparison, 80%/95% confidence bands.

### Route 04: Competitor Watch (`/competitors`)
- **Header:** "Competitor Intelligence & Buy Box Monitor".
- **Modules:**
  - Competitive Price Observation Grid with 3-tier matching indicators.
  - Buy Box status alerts (highlighting lost Buy Boxes).
  - Price Contradiction Banner (triggered when relative price spread > 15%).

### Route 05: Market Radar (`/market-radar`)
- **Header:** "Market Radar — Free Public News & Macro Signals".
- **Modules:**
  - GDELT News Feed: Stream of public trade and supply chain articles (`PUBLIC_NEWS`).
  - RSS News Digest: Category regulatory and e-commerce news.
  - Search Term Click Share: Top Brand Analytics search queries.

### Route 06: Product Opportunities (`/opportunities`)
- **Header:** "Product Opportunity Engine".
- **Modules:**
  - Itemized Attention Score leaderboard.
  - Component point breakdown (Inventory, Review, Listing, Pricing, Signals).
  - Estimated Revenue Unlock ($ that can be recovered).

### Route 07: Pricing Lab (`/pricing-lab`)
- **Header:** "Pricing Lab & Margin Simulator".
- **Modules:**
  - Interactive price slider testing margin changes.
  - Visual Fee Structure Waterfall (COGS $\to$ Fulfillment $\to$ Referral $\to$ Closing $\to$ Margin).
  - Inviolable Margin Floor boundary line.

### Route 08: Action Center (`/actions`)
- **Header:** "Operator Action Center (Decision Queue)".
- **Modules:**
  - Queue cards for pending recommendations.
  - Collapsible **"Why Panel"**:
    * *What happened?*
    * *Why does it matter?*
    * *Evidence & Calculation*
    * *What if nothing is done?*
    * *Recommended Action*
    * *Alternatives Considered*
  - Action Controls: `[Approve]` (Green), `[Reject]` (Red + modal requiring reason), `[Snooze 7 Days]` (Gray).

### Route 09: Automations (`/automations`)
- **Header:** "Durable Automation Rules".
- **Modules:**
  - Rule Builder form: Condition triggers and safety threshold bounds.
  - Active rules list with enable/disable toggles.
  - Execution audit history table.

### Route 10: Research Reports (`/reports`)
- **Header:** "Research Reports & Executive Briefs".
- **Modules:**
  - Weekly Brief generator.
  - Download buttons: `[Download Markdown]` and `[Print / PDF]`.
  - Verbatim citation appendix.

### Route 11: Data Connections & Settings (`/settings`)
- **Header:** "Data Connections, Compliance & Settings".
- **Modules:**
  - Amazon SP-API Health & Credentials card.
  - Local Ollama Service status and detected model card.
  - Strict Free-First Policy status card (`FREE_ONLY=true`).
  - Standardized CSV Data Import hub (Download Template, Upload File, Validation Table, Commit).
  - Database & System Diagnostics.

---

## 6. Responsive Viewport Adaptations

### 6.1 Desktop (1440px)
- Permanent 220px sidebar.
- Multi-column KPI strip (4–5 tiles).
- Side-by-side data table (65%) and inspector panel (35%).
- Full chart tooltips with hover crosshairs.

### 6.2 Tablet / Compact (1024px)
- Collapsible sidebar (hamburger toggle).
- 2-column KPI grid.
- Tables support horizontal scrolling with sticky first column (`SKU`).
- Inspector panel stacks below data table.

### 6.3 Mobile (390px)
- Bottom sheet drawer navigation (`components/ui/sheet.tsx`).
- Single-column KPI cards.
- Data tables collapse into stacked cards with expandable details.
- Header title and status badges truncate gracefully with zero horizontal scroll overflow (`scrollWidth === clientWidth`).

