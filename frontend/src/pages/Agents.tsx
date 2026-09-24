import { Bot, FlaskConical, Search, Sparkles, Waypoints } from 'lucide-react'
import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorState } from '@/components/shared/ErrorState'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { CardSkeleton } from '@/components/shared/Skeletons'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { formatDateTime, formatRelativeTime, titleCase } from '@/lib/utils'
import type { AgentStatus } from '@/lib/types'
import { useActivity } from '@/hooks/useActivity'
import { useAgents } from '@/hooks/useAgents'

const ICONS: Record<string, typeof Search> = {
  research_agent: Search,
  insight_agent: Sparkles,
  signal_detector: FlaskConical,
  orchestrator: Waypoints,
}

// The API's `agent` filter is an exact match against decision_log's
// `agent` field, and the 3 signal detectors log under their own
// module names, not "signal_detector" — so the trace for that card
// merges all three.
const LOG_AGENT_NAMES: Record<string, string[]> = {
  research_agent: ['research_agent'],
  insight_agent: ['insight_agent'],
  signal_detector: ['inventory_signal', 'ppc_waste_signal', 'rank_bb_signal'],
  orchestrator: ['orchestrator'],
}

export default function Agents() {
  const { data, isLoading, isError, refetch } = useAgents()
  const [expanded, setExpanded] = useState<string | null>(null)

  if (isError) {
    return (
      <AppShell title="AI Agents">
        <ErrorState description="Couldn't load agent status." onRetry={() => refetch()} />
      </AppShell>
    )
  }

  return (
    <AppShell title="AI Agents">
      <div className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          Specialized agents that research, ground, detect, and surface decisions — not a single chatbot.
        </p>
        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <CardSkeleton key={i} lines={4} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {(data ?? []).map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                expanded={expanded === agent.id}
                onToggle={() => setExpanded((v) => (v === agent.id ? null : agent.id))}
              />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}

function AgentCard({
  agent,
  expanded,
  onToggle,
}: {
  agent: AgentStatus
  expanded: boolean
  onToggle: () => void
}) {
  const Icon = ICONS[agent.id] ?? Bot
  const trace = useActivity({ limit: 300 })
  const entries = (trace.data ?? [])
    .filter((e) => LOG_AGENT_NAMES[agent.id]?.includes(e.agent))
    .slice(0, 8)

  return (
    <Card className="flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="rounded-lg border border-border bg-muted p-2">
            <Icon className="size-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">{agent.name}</p>
            <p className="text-xs text-muted-foreground">{agent.technology}</p>
          </div>
        </div>
        <StatusBadge status={agent.kind === 'live' ? 'LIVE' : 'SYNTHETIC'} />
      </div>
      <p className="text-sm text-muted-foreground">{agent.purpose}</p>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        {agent.mode && <Badge variant="outline">{agent.mode}</Badge>}
        <span>
          Status: <strong className="text-foreground">{titleCase(agent.status)}</strong>
        </span>
      </div>
      {agent.last_executed_at && (
        <p className="text-xs text-muted-foreground">
          Last: {titleCase(agent.last_action ?? '')} on {agent.last_product} ·{' '}
          {formatRelativeTime(agent.last_executed_at)}
        </p>
      )}
      {(agent.run_stats || agent.llm_invocation_count > 0) && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground sm:grid-cols-3">
          {agent.run_stats && (
            <>
              <Stat label="Runs" value={agent.run_stats.run_count} />
              <Stat label="Succeeded" value={agent.run_stats.success_count} />
              <Stat label="Failed" value={agent.run_stats.failure_count} />
              <Stat
                label="Avg duration"
                value={agent.run_stats.avg_duration_seconds != null ? `${agent.run_stats.avg_duration_seconds.toFixed(2)}s` : '—'}
              />
            </>
          )}
          <Stat label="AI calls" value={agent.llm_invocation_count} />
          <Stat label="AI available" value={`${agent.llm_available_count}/${agent.llm_invocation_count}`} />
        </div>
      )}
      <button
        onClick={onToggle}
        className="mt-1 self-start text-xs font-medium text-accent hover:underline"
      >
        {expanded ? 'Hide execution trace' : 'View execution trace'}
      </button>
      {expanded && (
        <div className="mt-1 flex flex-col gap-2 border-l border-border pl-3">
          {entries.length === 0 ? (
            <EmptyState title="No trace entries yet" className="border-none py-4" />
          ) : (
            entries.map((e, i) => (
              <div key={i} className="text-xs">
                <span className="font-medium text-foreground">{titleCase(e.action)}</span>{' '}
                <span className="text-muted-foreground">
                  · {e.product_name} · {formatDateTime(e.timestamp)}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </Card>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="font-semibold text-foreground">{value}</div>
      <div>{label}</div>
    </div>
  )
}
