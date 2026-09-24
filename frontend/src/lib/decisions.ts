import { SIGNAL_TYPE_LABEL } from './signalCopy'
import type { ActivityEvent, SignalType } from './types'
import { titleCase } from './utils'

// A human decision is just another decision_log entry (agent: "human"),
// filtered by product + category — there's no separate "status" field
// on a signal/insight, so every page that needs to know whether
// something has already been decided cross-references activity the
// same way. One implementation, reused everywhere.

export function findDecision(
  activity: ActivityEvent[] | undefined,
  productName: string,
  category: string,
): ActivityEvent | undefined {
  if (!activity) return undefined
  return activity.find(
    (e) =>
      e.agent === 'human' &&
      e.product_name === productName &&
      (e.detail as { category?: string } | undefined)?.category === category,
  )
}

export function decisionLabel(action: string): string {
  if (action === 'decision_approved') return 'Approved'
  if (action === 'decision_rejected') return 'Rejected'
  if (action === 'decision_more_research_requested') return 'More Research Requested'
  return action
}

export function decisionTone(action: string): 'success' | 'danger' | 'warning' | 'secondary' {
  if (action === 'decision_approved') return 'success'
  if (action === 'decision_rejected') return 'danger'
  if (action === 'decision_more_research_requested') return 'warning'
  return 'secondary'
}

// What a decision was actually about. A decision_log entry's `detail`
// shape differs by source: signal decisions log {category: SignalType},
// module decisions log {module, field}. Rendering either raw (or not at
// all) left "Approved" with a blank subject, or a raw snake_case value
// like "inventory_stockout", on Decision History / Decision Center.
export function decisionSubject(detail: Record<string, unknown> | null | undefined): string {
  if (!detail) return ''
  const category = detail.category as string | undefined
  if (category && category in SIGNAL_TYPE_LABEL) {
    return SIGNAL_TYPE_LABEL[category as SignalType]
  }
  const module = detail.module as string | undefined
  if (module) {
    const field = detail.field as string | undefined
    return field ? `${titleCase(module)} · ${titleCase(field)}` : titleCase(module)
  }
  return ''
}
