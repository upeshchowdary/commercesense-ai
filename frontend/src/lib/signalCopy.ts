import type { DetectedSignal, SignalType } from './types'

// Plain-language copy for the 3 deterministic synthetic detectors.
// This is template text keyed off real evidence fields — never an AI
// judgment, and never presented as one (signal_type is a closed,
//3-value set, checked exhaustively below).

function num(v: unknown): number {
  return typeof v === 'number' ? v : Number(v ?? 0)
}

export function signalSummary(signal: DetectedSignal): string {
  const e = signal.evidence
  switch (signal.signal_type) {
    case 'inventory_stockout':
      return `${num(e.days_of_stock_remaining)} day(s) of stock remain at the current sales pace (${num(e.current_inventory)} units on hand, ~${num(e.avg_daily_sales_last_14d)}/day sold) — below the ${num(e.threshold_days)}-day safety threshold.`
    case 'ppc_waste':
      return `Ad cost of sale (ACOS) stayed above ${Math.round(num(e.threshold_acos) * 100)}% for ${num(e.days_over_threshold)} of the last ${num(e.window_days)} days (average ${Math.round(num(e.avg_acos_last_window) * 100)}%) — $${num(e.total_ad_spend_last_window).toFixed(2)} spent for $${num(e.total_ad_sales_last_window).toFixed(2)} in ad-attributed sales.`
    case 'rank_drop':
      return `Sales rank worsened ${num(e.rank_pct_worse)}% over ${num(e.rank_window_days)} days (from #${num(e.rank_start)} to #${num(e.rank_end)})${e.buybox_flagged ? `, and the Buy Box was lost on ${num(e.days_without_buybox)} of the last ${num(e.buybox_window_days)} days` : ''}.`
    default:
      return 'Signal detected.'
  }
}

const WHY_IT_MATTERS: Record<SignalType, string> = {
  inventory_stockout:
    "Going out of stock stalls sales momentum immediately, and Amazon's ranking algorithm penalizes listings that become unavailable — the recovery in organic rank after a stockout usually takes longer than the stockout itself.",
  ppc_waste:
    "Ad spend that isn't converting into profitable sales is a direct, ongoing cost with no offsetting return — every additional day at this ACOS is margin spent for effectively nothing.",
  rank_drop:
    'A falling rank and a lost Buy Box compound each other: fewer buyers see the listing, which further reduces sales velocity, which further hurts rank and Buy Box eligibility.',
}

export function signalWhyItMatters(signalType: SignalType): string {
  return WHY_IT_MATTERS[signalType]
}

const RECOMMENDATION: Record<SignalType, string> = {
  inventory_stockout:
    'Reorder inventory now. At the current sales pace this product will run out before a standard replenishment cycle would complete.',
  ppc_waste:
    'Pause or reduce spend on the underperforming campaigns/keywords for this product, or lower bids until ACOS returns under threshold.',
  rank_drop:
    'Investigate the ranking and Buy Box loss: check price competitiveness, inventory health, and any recent listing or account-health issues.',
}

export function signalRecommendation(signalType: SignalType): string {
  return RECOMMENDATION[signalType]
}

export const SIGNAL_TYPE_LABEL: Record<SignalType, string> = {
  inventory_stockout: 'Inventory Stockout',
  ppc_waste: 'PPC Waste',
  rank_drop: 'Ranking / Buy Box Drop',
}
