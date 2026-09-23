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

export interface EvaluationResult {
  signals_have_been_run: boolean
  products_tested: number
  days_simulated: number
  seed: number
  planted_cases: number
  detected_cases: number
  false_positives: number
  results: EvalRow[]
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
