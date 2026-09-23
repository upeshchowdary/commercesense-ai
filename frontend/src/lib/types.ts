// Mirrors the verified response/request shapes of the FastAPI layer
// (api/routers/*.py, api/schemas.py). Nothing here is invented —
// every field was confirmed against a live response.

export type SignalType = 'inventory_stockout' | 'ppc_waste' | 'rank_drop'
export type Severity = 'high' | 'medium'
export type Confidence = 'none' | 'low' | 'medium' | 'high'
export type InsightCategory = 'pricing' | 'trend' | 'risk' | 'opportunity'
export type DecisionChoice = 'approved' | 'rejected' | 'more_research_requested'
export type AgentKind = 'live' | 'synthetic'

export interface ProductSummary {
  product_id: string
  name: string
  category: string
  base_price: number
  signal_count: number
  highest_severity: Severity | null
  planted_issue: SignalType | null
}

export interface DailyMetric {
  product_id: string
  date: string
  units_sold: number
  inventory_level: number
  rank: number
  has_buy_box: 0 | 1
  ad_spend: number
  ad_clicks: number
  ad_sales: number
}

export interface DetectedSignal {
  id: number
  product_id: string
  date: string
  signal_type: SignalType
  severity: Severity
  evidence: Record<string, unknown>
  detected_at: string
  product_name?: string
}

export interface ActivityEvent {
  timestamp: string
  agent: string
  product_name: string
  action: string
  detail: Record<string, unknown>
}

export interface ProductDetail {
  product_id: string
  name: string
  category: string
  base_price: number
  planted_issue: SignalType | null
  metrics: DailyMetric[]
  signals: DetectedSignal[]
  activity: ActivityEvent[]
}

export interface SearchFinding {
  query: string
  source_url: string
  snippet: string
  retrieved_at: string
}

export interface ResearchBundle {
  product_name: string
  findings: SearchFinding[]
  search_queries_used: string[]
  gathered_at: string
}

export interface ResearchResult {
  bundle: ResearchBundle
  cache_hit: boolean
  cache_age_seconds: number | null
}

export interface Insight {
  category: InsightCategory
  summary: string | null
  confidence: Confidence
  source_snippet: string | null
  source_url: string | null
}

export interface InsightReport {
  product_name: string
  insights: Insight[]
  generated_at: string
  grounded_count: number
  ungrounded_count: number
}

export interface IntelligenceResult {
  bundle: ResearchBundle
  report: InsightReport
}

export interface EvalRow {
  product_id: string
  product: string
  signal: SignalType | null
  expected: boolean
  detected: boolean
  false_positive: boolean
  result: 'PASS' | 'FAIL'
}

export interface IntelligenceEvalModuleSummary {
  tp: number
  fp: number
  tn: number
  fn: number
  precision: number | null
  recall: number | null
  f1: number | null
}

export interface IntelligenceEvalRow {
  product_id: string
  product: string
  expected: boolean
  detected: boolean | null
  result: 'TP' | 'FP' | 'TN' | 'FN' | 'NO_DATA'
}

export interface IntelligenceEvaluation {
  data_available: boolean
  message?: string
  results?: { listing: IntelligenceEvalRow[]; pricing: IntelligenceEvalRow[]; review: IntelligenceEvalRow[] }
  summary?: { listing: IntelligenceEvalModuleSummary; pricing: IntelligenceEvalModuleSummary; review: IntelligenceEvalModuleSummary }
}

export interface EvaluationResult {
  signals_have_been_run: boolean
  products_tested: number
  days_simulated: number
  seed: number
  planted_cases: number
  detected_cases: number
  false_positives: number
  results: EvalRow[]
  intelligence_modules: IntelligenceEvaluation
}

export interface AgentStatus {
  id: string
  name: string
  technology: string
  purpose: string
  kind: AgentKind
  mode?: string
  last_action: string | null
  last_product: string | null
  last_executed_at: string | null
  status: 'idle' | 'never_run'
}

export interface SignalRunResult {
  inventory_stockout_flagged: number
  ppc_waste_flagged: number
  rank_drop_flagged: number
  total_flagged: number
  ran_at: string
}

export interface HealthStatus {
  status: string
  gemini_api_key_set: boolean
  tavily_api_key_set: boolean
}

export interface DecisionRequest {
  product_name: string
  category: string
  decision: DecisionChoice
  reason?: string
  decided_by?: string
}

export interface DecisionResponse {
  recorded: boolean
  action: string
}

// ---------------------------------------------------- Intelligence modules

export type Provenance = 'LIVE' | 'CACHED' | 'SYNTHETIC' | 'DEMO'
export type InventoryCategory = 'STOCKOUT_RISK' | 'LOW_COVER' | 'HEALTHY' | 'OVERSTOCK' | 'SLOW_MOVING' | 'NO_DATA'
export type PriceState = 'BELOW_MARGIN_FLOOR' | 'HEALTHY_RANGE' | 'ABOVE_COMPETITIVE_RANGE' | 'COMPETITIVE_PRESSURE' | 'UNKNOWN'

export interface AiExplanation {
  available: boolean
  provider: string
  model: string
  message: string | null
  error: string | null
  data: Record<string, unknown> | null
}

export interface IntelligenceApproveRequest {
  decision: DecisionChoice
  field?: string
  reason?: string
  decided_by?: string
}

// --- Listing ---
export interface ListingData {
  product_id: string
  title: string
  brand: string
  product_type: string
  bullets: string[]
  description: string
  attributes: Record<string, unknown>
  image_count: number
  image_urls: string[]
  listing_status: string
}

export interface ListingScoreResult {
  score: number
  category_scores: Record<string, number>
  failed_rules: string[]
  warnings: string[]
  passed_rules: string[]
}

export interface ListingIntelligenceResult extends ListingScoreResult {
  provenance: Provenance
  product_id: string
  listing: ListingData
  ai_diagnosis?: AiExplanation
}

export interface ListingRewriteResult {
  provenance: Provenance
  product_id: string
  recommendation_id?: number
  current_title?: string
  proposed_title: string | null
  changes?: string[]
  message?: string | null
  grounding?: { grounded: boolean; unsupported_numbers: string[]; reason: string | null }
}

// --- Pricing ---
export interface PricingObservation {
  id: number
  competitor: string
  price: number
  currency: string
  source: string
  source_url: string | null
  observed_at: string
  confidence: string
  is_verified: number
}

export interface PricingIntelligenceResult {
  provenance: Provenance
  product_id: string
  current_price: number
  cost_inputs: { cogs: number; referral_fee_pct: number; fulfillment_fee: number; other_cost: number; target_margin_pct: number; currency: string }
  contribution: { variable_cost: number; contribution: number; margin_pct: number | null }
  breakeven_price: number | null
  target_margin_price: number | null
  price_distribution: { lowest: number | null; highest: number | null; median: number | null; average: number | null; pct_diff_from_median: number | null; sample_size: number }
  observations: PricingObservation[]
  price_state: PriceState
  recommendation: { low: number | null; high: number | null; reasoning: string[]; confidence: string }
  ai_explanation?: AiExplanation
}

// --- Review ---
export interface ReviewThemeResult {
  theme: string
  mentions: number
  negative: number
  neutral: number
  positive: number
  evidence: { id: number | null; rating: number; review_text: string; review_date: string }[]
}

export interface EmergingIssue {
  theme: string
  previous_period_mentions: number
  current_period_mentions: number
  window_days: number
  explanation: string
}

export interface ReviewIntelligenceResult {
  provenance: Provenance
  product_id: string
  category: string
  rating_stats: {
    total_reviews: number
    avg_rating: number | null
    rating_distribution: Record<string, { count: number; pct: number }>
    negative_pct: number | null
  }
  velocity: { window_days: number; current_count: number; previous_count: number; pct_change: number | null; trend: string }
  themes: ReviewThemeResult[]
  emerging_issues: EmergingIssue[]
  total_reviews_available: number
  ai_summary?: AiExplanation
}

// --- Inventory ---
export interface InventoryIntelligenceResult {
  provenance: Provenance
  product_id: string
  current_inventory: number
  demand: { avg_7d: number; avg_14d: number; avg_30d: number; weighted_avg: number }
  config: { lead_time_days: number; safety_days: number; moq: number | null; reorder_multiple: number | null }
  days_of_cover: number | null
  reorder_point: number
  safety_stock: number
  category: InventoryCategory
  suggested_reorder_quantity: number
  projected_stockout_date: string | null
  excess_inventory: { current_units: number; expected_demand_90d: number; days_of_cover: number; excess_units_estimate: number } | null
  data_sufficient: boolean
  ai_explanation?: AiExplanation
}

export interface InventoryForecastRow {
  day_offset: number
  date: string
  projected_inventory: number
  inbound_qty: number
}

export interface InventoryWhatIfResult {
  provenance: Provenance
  simulation: boolean
  product_id: string
  lead_time_days: number
  reorder_quantity: number
  inventory_at_arrival: number
  post_replenishment_inventory: number
  days_of_cover_after_replenishment: number | null
  stockout_risk_before_arrival: boolean
}

// --- Opportunity / Product Bundle View ---
export interface ProductIntelligenceOverview {
  provenance: Provenance
  product: ProductSummary
  attention_score: number
  components: {
    inventory_risk: number
    review_risk: number
    listing_issues: number
    pricing_pressure: number
    existing_signals: number
  }
  listing_score: number | null
  price_state: PriceState
  inventory_category: InventoryCategory
  review_negative_pct: number | null
  review_has_emerging_issue: boolean
  existing_signal_count: number
  top_issues: string[]
}
