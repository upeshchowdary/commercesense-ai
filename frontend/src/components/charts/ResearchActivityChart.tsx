import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { ActivityEvent } from '@/lib/types'
import { CHART_COLORS, tooltipContentStyle, tooltipLabelStyle } from './chart-theme'

export function ResearchActivityChart({ activity }: { activity: ActivityEvent[] }) {
  const liveRuns = activity.filter((e) => e.action === 'live_search').length
  const cacheHits = activity.filter((e) => e.action === 'cache_hit').length
  const data = [
    { name: 'Live Runs', value: liveRuns, color: CHART_COLORS.blue },
    { name: 'Cache Hits', value: cacheHits, color: CHART_COLORS.amber },
  ].filter((d) => d.value > 0)

  if (data.length === 0) {
    return (
      <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
        No research runs yet
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Tooltip contentStyle={tooltipContentStyle} labelStyle={tooltipLabelStyle} />
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={3}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color} stroke="var(--panel)" strokeWidth={2} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  )
}
