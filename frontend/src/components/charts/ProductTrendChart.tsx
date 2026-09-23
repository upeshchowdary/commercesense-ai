import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DailyMetric } from '@/lib/types'
import { axisTickStyle, CHART_COLORS, tooltipContentStyle, tooltipLabelStyle } from './chart-theme'

function shortDate(d: string) {
  const date = new Date(d)
  return Number.isNaN(date.getTime()) ? d : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function RankTrendChart({ metrics }: { metrics: DailyMetric[] }) {
  const data = metrics.map((m) => ({ date: shortDate(m.date), rank: m.rank }))
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
        <XAxis dataKey="date" tick={axisTickStyle} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} minTickGap={30} />
        <YAxis reversed tick={axisTickStyle} axisLine={false} tickLine={false} width={40} />
        <Tooltip contentStyle={tooltipContentStyle} labelStyle={tooltipLabelStyle} />
        <Line type="monotone" dataKey="rank" name="Sales Rank" stroke={CHART_COLORS.blue} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function InventoryTrendChart({ metrics }: { metrics: DailyMetric[] }) {
  const data = metrics.map((m) => ({ date: shortDate(m.date), inventory: m.inventory_level }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
        <XAxis dataKey="date" tick={axisTickStyle} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} minTickGap={30} />
        <YAxis tick={axisTickStyle} axisLine={false} tickLine={false} width={36} />
        <Tooltip contentStyle={tooltipContentStyle} labelStyle={tooltipLabelStyle} />
        <Line type="monotone" dataKey="inventory" name="Inventory" stroke={CHART_COLORS.amber} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function AcosTrendChart({ metrics }: { metrics: DailyMetric[] }) {
  const data = metrics.map((m) => ({
    date: shortDate(m.date),
    acos: m.ad_sales > 0 ? m.ad_spend / m.ad_sales : 0,
  }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
        <XAxis dataKey="date" tick={axisTickStyle} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} minTickGap={30} />
        <YAxis tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={axisTickStyle} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          formatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
        />
        <Line type="monotone" dataKey="acos" name="ACOS" stroke={CHART_COLORS.red} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
