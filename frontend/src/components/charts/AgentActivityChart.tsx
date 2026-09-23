import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ActivityEvent } from '@/lib/types'
import { titleCase } from '@/lib/utils'
import { axisTickStyle, CHART_COLORS, tooltipContentStyle, tooltipLabelStyle } from './chart-theme'

export function AgentActivityChart({ activity }: { activity: ActivityEvent[] }) {
  const counts = new Map<string, number>()
  for (const e of activity) {
    counts.set(e.agent, (counts.get(e.agent) ?? 0) + 1)
  }
  const data = Array.from(counts.entries())
    .map(([agent, count]) => ({ agent: titleCase(agent), count }))
    .sort((a, b) => b.count - a.count)

  if (data.length === 0) {
    return (
      <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
        No agent activity yet
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
        <XAxis type="number" allowDecimals={false} tick={axisTickStyle} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="agent" tick={axisTickStyle} axisLine={false} tickLine={false} width={110} />
        <Tooltip contentStyle={tooltipContentStyle} labelStyle={tooltipLabelStyle} cursor={{ fill: 'var(--panel-border)', opacity: 0.3 }} />
        <Bar dataKey="count" name="Events" fill={CHART_COLORS.blue} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
