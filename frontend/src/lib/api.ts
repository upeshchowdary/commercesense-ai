import type {
  ActivityEvent,
  ActivityStats,
  AgentStatus,
  CsvImportResult,
  CsvTemplate,
  CsvValidationResult,
  DecisionRequest,
  DecisionResponse,
  DetectedSignal,
  EvaluationResult,
  PricingSimulateResult,
  HealthStatus,
  ImportDataType,
  IntelligenceApproveRequest,
  IntelligenceResult,
  InventoryForecastRow,
  InventoryIntelligenceResult,
  InventoryWhatIfResult,
  ListingIntelligenceResult,
  ListingRewriteResult,
  PricingIntelligenceResult,
  ProductDetail,
  ProductIntelligenceOverview,
  ProductSummary,
  ReviewIntelligenceResult,
  SignalRunResult,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const API_BASE = (import.meta as any).env?.VITE_API_URL
  ? `${(import.meta as any).env.VITE_API_URL.replace(/\/$/, '')}/api`
  : '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  if (entries.length === 0) return ''
  return `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()}`
}

export const getHealth = () => request<HealthStatus>('/health')

export const getProducts = () => request<ProductSummary[]>('/products')

export const getProduct = (productId: string) => request<ProductDetail>(`/products/${encodeURIComponent(productId)}`)

export const runSignalDetection = () => request<SignalRunResult>('/signals/run', { method: 'POST' })

export const getSignals = (filters?: { severity?: string; type?: string; product_id?: string }) =>
  request<DetectedSignal[]>(`/signals${qs(filters ?? {})}`)

export const getSignal = (id: number) => request<DetectedSignal>(`/signals/${id}`)

export const postResearch = (body: { product_name: string; use_cache?: boolean; generate_summary?: boolean }) =>
  request<any>('/v1/research/analyze', { method: 'POST', body: JSON.stringify(body) })

export const postIntelligence = (body: { product_name: string; use_cache?: boolean }) =>
  request<IntelligenceResult>('/intelligence/run', { method: 'POST', body: JSON.stringify(body) })

export const getActivity = (filters?: {
  product_name?: string
  agent?: string
  action?: string
  limit?: number
}) => request<ActivityEvent[]>(`/activity${qs(filters ?? {})}`)

export const getActivityStats = () => request<ActivityStats>('/activity/stats')

export const postDecision = (body: DecisionRequest) =>
  request<DecisionResponse>('/decisions', { method: 'POST', body: JSON.stringify(body) })

export const getEvaluation = () => request<EvaluationResult>('/evaluation')

export const getAgents = () => request<AgentStatus[]>('/agents')

// ---------------------------------------------------- Intelligence modules

export const getListingIntelligence = (productId: string) =>
  request<ListingIntelligenceResult>(`/listing-intelligence/${encodeURIComponent(productId)}`)
export const postListingAnalyze = (productId: string) =>
  request<ListingIntelligenceResult>(`/listing-intelligence/${encodeURIComponent(productId)}/analyze`, { method: 'POST' })
export const postListingRewrite = (productId: string, useAi = true) =>
  request<ListingRewriteResult>(`/listing-intelligence/${encodeURIComponent(productId)}/rewrite`, {
    method: 'POST', body: JSON.stringify({ use_ai: useAi }),
  })
export const postListingApprove = (productId: string, body: IntelligenceApproveRequest) =>
  request<DecisionResponse>(`/listing-intelligence/${encodeURIComponent(productId)}/approve`, { method: 'POST', body: JSON.stringify(body) })

export const getPricingIntelligence = (productId: string) =>
  request<PricingIntelligenceResult>(`/pricing-intelligence/${encodeURIComponent(productId)}`)
export const postPricingAnalyze = (productId: string, useLiveResearch = false) =>
  request<PricingIntelligenceResult>(`/pricing-intelligence/${encodeURIComponent(productId)}/analyze`, {
    method: 'POST', body: JSON.stringify({ use_live_research: useLiveResearch }),
  })
export const postPricingSimulate = (productId: string, newPrice: number, adSpendLevels?: number[]) =>
  request<PricingSimulateResult>(`/pricing-intelligence/${encodeURIComponent(productId)}/simulate`, {
    method: 'POST', body: JSON.stringify({ new_price: newPrice, ad_spend_levels: adSpendLevels }),
  })
export const postPricingApprove = (productId: string, body: IntelligenceApproveRequest) =>
  request<DecisionResponse>(`/pricing-intelligence/${encodeURIComponent(productId)}/approve`, { method: 'POST', body: JSON.stringify(body) })

export const getReviewIntelligence = (productId: string) =>
  request<ReviewIntelligenceResult>(`/review-intelligence/${encodeURIComponent(productId)}`)
export const postReviewAnalyze = (productId: string) =>
  request<ReviewIntelligenceResult>(`/review-intelligence/${encodeURIComponent(productId)}/analyze`, { method: 'POST' })
export const postReviewApprove = (productId: string, body: IntelligenceApproveRequest) =>
  request<DecisionResponse>(`/review-intelligence/${encodeURIComponent(productId)}/approve`, { method: 'POST', body: JSON.stringify(body) })

export const getInventoryIntelligence = (productId: string) =>
  request<InventoryIntelligenceResult>(`/inventory-intelligence/${encodeURIComponent(productId)}`)
export const postInventoryAnalyze = (productId: string) =>
  request<InventoryIntelligenceResult>(`/inventory-intelligence/${encodeURIComponent(productId)}/analyze`, { method: 'POST' })
export const postInventoryForecast = (
  productId: string,
  daysAhead = 30,
  inbound: { day_offset: number; quantity: number }[] = [],
) =>
  request<{ provenance: string; product_id: string; rows: InventoryForecastRow[] }>(
    `/inventory-intelligence/${encodeURIComponent(productId)}/forecast`,
    { method: 'POST', body: JSON.stringify({ days_ahead: daysAhead, inbound }) },
  )
export const postInventorySimulate = (productId: string, reorderQuantity: number, leadTimeDays?: number) =>
  request<InventoryWhatIfResult>(`/inventory-intelligence/${encodeURIComponent(productId)}/simulate`, {
    method: 'POST', body: JSON.stringify({ reorder_quantity: reorderQuantity, lead_time_days: leadTimeDays }),
  })
export const postInventoryApprove = (productId: string, body: IntelligenceApproveRequest) =>
  request<DecisionResponse>(`/inventory-intelligence/${encodeURIComponent(productId)}/approve`, { method: 'POST', body: JSON.stringify(body) })

export const getProductIntelligenceOverview = (productId: string) =>
  request<ProductIntelligenceOverview>(`/products/${encodeURIComponent(productId)}/intelligence`)

// ---------------------------------------------------------------- CSV import (spec §25)

async function requestFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`/api${path}`, { method: 'POST', body: form })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

export const getImportTemplate = (dataType: ImportDataType) =>
  request<CsvTemplate>(`/data-import/template/${dataType}`)
export const postValidateCsv = (dataType: ImportDataType, file: File) =>
  requestFile<CsvValidationResult>(`/data-import/${dataType}/validate`, file)
export const postCommitCsv = (dataType: ImportDataType, file: File) =>
  requestFile<CsvImportResult>(`/data-import/${dataType}/commit`, file)


// =====================================================================
// CommerceSense AI v3 Extended APIs
// =====================================================================

export const getCompetitorObservations = (productId: string) =>
  request<any>(`/v1/competitors/${encodeURIComponent(productId)}`)

export const getCompetitorMatches = (productId: string) =>
  request<any>(`/v1/competitors/${encodeURIComponent(productId)}/matches`)

export const postReviewCandidateMatch = (matchId: number, confirmed: boolean, productId: string = 'P001') =>
  request<any>(`/v1/competitors/${encodeURIComponent(productId)}/matches/${matchId}/review`, {
    method: 'POST',
    body: JSON.stringify({ confirmed }),
  })

export const postSyncCompetitor = (productId: string) =>
  request<any>(`/v1/competitors/${encodeURIComponent(productId)}/sync`, {
    method: 'POST',
  })

export const getMarketRadarTopics = () =>
  request<any[]>('/v1/market-radar/topics')

export const getMarketRadarNews = () =>
  request<any[]>('/v1/market-radar/news')

export const getGoogleTrends = (keyword: string) =>
  request<any>(`/v1/market-radar/trends?keyword=${encodeURIComponent(keyword)}`)

export const getOpportunities = (category?: string) =>
  request<any[]>(`/v1/opportunities${category ? `?category=${encodeURIComponent(category)}` : ''}`)

export const postEvaluateOpportunity = (data: Record<string, any>) =>
  request<any>('/v1/opportunities/evaluate', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const getActions = (filters?: { status?: string; product_id?: string }) =>
  request<any[]>(`/v1/actions${qs(filters ?? {})}`)

export const postDecideAction = (
  actionId: number,
  decision: 'APPROVED' | 'REJECTED' | 'SNOOZED',
  reason?: string,
  snoozeDays = 7,
) =>
  request<any>(`/v1/actions/${actionId}/decide`, {
    method: 'POST',
    body: JSON.stringify({
      decision,
      actor: 'Seller Operator',
      reason,
      snooze_days: snoozeDays,
    }),
  })

export const getAutomationRules = () =>
  request<any[]>('/v1/automations/rules')

export const patchAutomationRule = (ruleId: number, updates: Record<string, any>) =>
  request<any>(`/v1/automations/rules/${ruleId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

export const postEvaluateAutomations = () =>
  request<any>('/v1/automations/evaluate', { method: 'POST' })

export const getAuditEvents = (limit = 100) =>
  request<any[]>(`/v1/audit/events?limit=${limit}`)

export const postLiveResearch = (body: { product_name: string; use_cache?: boolean; generate_summary?: boolean }) =>
  request<any>('/v1/research/analyze', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const postAddProduct = (product: {
  product_id: string
  name: string
  category: string
  base_price: number
  cogs?: number
}) =>
  request<any>('/products', {
    method: 'POST',
    body: JSON.stringify(product),
  })


export const getConnectionsStatus = () =>
  request<any>('/v1/connections/status')

export const getRotatorStatus = () =>
  request<any>('/v1/connections/rotator')
