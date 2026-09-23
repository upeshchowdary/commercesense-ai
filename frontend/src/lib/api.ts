import type {
  ActivityEvent,
  AgentStatus,
  DecisionRequest,
  DecisionResponse,
  DetectedSignal,
  EvaluationResult,
  HealthStatus,
  IntelligenceResult,
  ProductDetail,
  ProductSummary,
  ResearchResult,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
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

export const postResearch = (body: { product_name: string; use_cache?: boolean }) =>
  request<ResearchResult>('/research', { method: 'POST', body: JSON.stringify(body) })

export const postIntelligence = (body: { product_name: string; use_cache?: boolean }) =>
  request<IntelligenceResult>('/intelligence/run', { method: 'POST', body: JSON.stringify(body) })

export const getActivity = (filters?: {
  product_name?: string
  agent?: string
  action?: string
  limit?: number
}) => request<ActivityEvent[]>(`/activity${qs(filters ?? {})}`)

export const postDecision = (body: DecisionRequest) =>
  request<DecisionResponse>('/decisions', { method: 'POST', body: JSON.stringify(body) })

export const getEvaluation = () => request<EvaluationResult>('/evaluation')

export const getAgents = () => request<AgentStatus[]>('/agents')
