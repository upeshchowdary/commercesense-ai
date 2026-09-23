import type { CSSProperties } from 'react'

// Shared Recharts styling so every chart in the app reads as one system.
export const CHART_COLORS = {
  grid: 'var(--panel-border)',
  axis: 'var(--text-faint)',
  text: 'var(--text-muted)',
  amber: 'var(--amber)',
  blue: 'var(--blue)',
  blueDeep: 'var(--blue-deep)',
  green: 'var(--green)',
  red: 'var(--red)',
  yellow: 'var(--yellow)',
}

export const tooltipContentStyle: CSSProperties = {
  background: 'var(--panel-elevated)',
  border: '1px solid var(--panel-border)',
  borderRadius: 10,
  fontSize: 12,
  color: 'var(--text)',
  boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
}

export const tooltipLabelStyle: CSSProperties = {
  color: 'var(--text-muted)',
  fontSize: 11,
  marginBottom: 4,
}

export const axisTickStyle = { fill: 'var(--text-faint)', fontSize: 11 }
