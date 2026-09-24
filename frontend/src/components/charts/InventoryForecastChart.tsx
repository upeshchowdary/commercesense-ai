import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { InventoryForecastRow } from '@/lib/types'
import { axisTickStyle, CHART_COLORS, tooltipContentStyle, tooltipLabelStyle } from './chart-theme'

function shortDate(d: string) {
  const date = new Date(d)
  return Number.isNaN(date.getTime())
    ? d
    : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

// This is a projected scenario, not observed history -- every point here
// is SYNTHETIC/computed, never mixed with or drawn like real past data.
export function InventoryForecastChart({
  rows,
  reorderPoint,
}: {
  rows: InventoryForecastRow[]
  reorderPoint: number
}) {
  if (rows.length === 0) {
    return (
      <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
        No forecast data yet
      </div>
    )
  }

  const data = rows.map((r) => ({ ...r, label: shortDate(r.date) }))
  const stockoutRow = data.find((r) => r.projected_inventory <= 0)
  const inboundRows = data.filter((r) => r.inbound_qty > 0)

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
        <XAxis dataKey="label" tick={axisTickStyle} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} minTickGap={24} />
        <YAxis
          allowDecimals={false}
          // Recharts' default 'auto' domain fits only the Line's own
          // data, not the ReferenceLine -- when every projected value is
          // 0 (e.g. already out of stock with nothing inbound), the
          // reorder-point line at 195 landed off the top of the chart.
          domain={[0, (dataMax: number) => Math.max(dataMax, reorderPoint) * 1.1]}
          tick={axisTickStyle}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          formatter={(value, name) => (name === 'inbound_qty' && !value ? undefined : [value, name])}
        />
        <ReferenceLine
          y={reorderPoint}
          stroke={CHART_COLORS.amber}
          strokeDasharray="4 4"
          label={{ value: 'Reorder point', position: 'insideTopRight', fill: CHART_COLORS.amber, fontSize: 11 }}
        />
        {stockoutRow && (
          <ReferenceDot
            x={stockoutRow.label}
            y={stockoutRow.projected_inventory}
            r={5}
            fill={CHART_COLORS.red}
            stroke="none"
            label={{ value: 'Stockout', position: 'top', fill: CHART_COLORS.red, fontSize: 11 }}
          />
        )}
        {inboundRows.map((r) => (
          <ReferenceDot
            key={r.day_offset}
            x={r.label}
            y={r.projected_inventory}
            r={5}
            fill={CHART_COLORS.green}
            stroke="none"
            label={{ value: `+${r.inbound_qty}`, position: 'top', fill: CHART_COLORS.green, fontSize: 11 }}
          />
        ))}
        <Line
          type="monotone"
          dataKey="projected_inventory"
          name="Projected inventory"
          stroke={CHART_COLORS.blue}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
