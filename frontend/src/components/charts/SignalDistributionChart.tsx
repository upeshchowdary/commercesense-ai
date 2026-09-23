import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DetectedSignal } from '@/lib/types'
import { titleCase } from '@/lib/utils'
import { axisTickStyle, CHART_COLORS, tooltipContentStyle, tooltipLabelStyle } from './chart-theme'

const SEVERITY_COLOR: Record<string, string> = {
  high: CHART_COLORS.red,
  medium: CHART_COLORS.amber,
}

export function SignalDistributionChart({ signals }: { signals: DetectedSignal[] }) {
  const byType = new Map<string, { type: string; high: number; medium: number }>()
  for (const s of signals) {
    const entry = byType.get(s.signal_type) ?? { type: s.signal_type, high: 0, medium: 0 }
    if (s.severity === 'high') entry.high += 1
    else entry.medium += 1
    byType.set(s.signal_type, entry)
  }
  const data = Array.from(byType.values()).map((d) => ({
    name: titleCase(d.type),
    High: d.high,
    Medium: d.medium,
  }))

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">
        No signals detected yet
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barCategoryGap={20}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
        <XAxis dataKey="name" tick={axisTickStyle} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
        <YAxis allowDecimals={false} tick={axisTickStyle} axisLine={false} tickLine={false} width={28} />
        <Tooltip contentStyle={tooltipContentStyle} labelStyle={tooltipLabelStyle} cursor={{ fill: 'var(--panel-border)', opacity: 0.3 }} />
        <Bar dataKey="High" stackId="a" fill={SEVERITY_COLOR.high} radius={[0, 0, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} />
          ))}
        </Bar>
        <Bar dataKey="Medium" stackId="a" fill={SEVERITY_COLOR.medium} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
