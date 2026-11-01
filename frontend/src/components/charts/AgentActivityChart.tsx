import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { titleCase } from '@/lib/utils'
import { axisTickStyle, CHART_COLORS, tooltipContentStyle, tooltipLabelStyle } from './chart-theme'

// Takes the full-log by_agent counts from GET /api/activity/stats, not a
// capped activity list -- a single bulk action (e.g. running signal
// detection, ~84 events) used to push older agents' events out of the
// previous 100-row window and undercount them here.
export function AgentActivityChart({ byAgent }: { byAgent: Record<string, number> }) {
  const data = Object.entries(byAgent)
    .filter(([agent]) => agent)
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
