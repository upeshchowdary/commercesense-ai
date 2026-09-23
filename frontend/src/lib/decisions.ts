import type { ActivityEvent } from './types'

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
