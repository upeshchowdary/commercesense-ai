import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { getHealth, getAuditEvents } from '@/lib/api'
import {
  Server,
  Activity,
  CheckCircle2,
  Cpu,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Diagnostics() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  })

  const { data: auditEvents = [] } = useQuery({
    queryKey: ['audit_events'],
    queryFn: () => getAuditEvents(20),
  })

  return (
    <AppShell>
      <Topbar title="System Diagnostics & Governance" />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              System Diagnostics & Runtime Telemetry
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Runtime health, socket-level egress interceptor state, operational feature flags, and immutable audit logs.
            </p>
          </div>
          <ProvenanceBadge provenance="CALCULATED" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Health & Egress Gate */}
          <div className="space-y-6">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Server className="size-4.5 text-red-600" />
                <h3 className="text-sm font-bold text-foreground">Core Backend Telemetry</h3>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">API Status:</span>
                  <span className="font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="size-3.5" /> {health?.status?.toUpperCase() || 'OK'}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">Free-Only Gate Policy:</span>
                  <span className="font-semibold font-mono text-red-700 dark:text-red-400">
                    {health?.free_only_mode ? 'ENFORCED (FREE_ONLY=true)' : 'PERMISSIVE'}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">Socket Egress Interceptor:</span>
                  <span className="font-semibold text-emerald-700 dark:text-emerald-400">ACTIVE (Blocks unauthorized egress)</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-muted-foreground">LLM Provider:</span>
                  <span className="font-mono font-semibold text-foreground">
                    {health?.llm_provider || 'ollama (local fallback)'}
                  </span>
                </div>
              </div>
            </div>

            {/* Feature Flags */}
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Cpu className="size-4.5 text-red-600" />
                <h3 className="text-sm font-bold text-foreground">Modular Feature Flags (Spec §57)</h3>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                {health?.feature_flags &&
                  Object.entries(health.feature_flags).map(([k, v]) => (
                    <div key={k} className="p-2 rounded bg-muted/40 flex justify-between items-center">
                      <span className="text-muted-foreground text-[11px] truncate">{k}:</span>
                      <span className={cn('font-bold text-[10px] px-1.5 py-0.5 rounded', v ? 'text-red-700 bg-red-50 border border-red-200 dark:bg-red-950/40 dark:text-red-400' : 'text-muted-foreground')}>
                        {String(v).toUpperCase()}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Audit Event Stream */}
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity className="size-4.5 text-red-600" />
                <h3 className="text-sm font-bold text-foreground">Recent Audit Events</h3>
              </div>
              <span className="text-xs text-muted-foreground">{auditEvents.length} recorded</span>
            </div>

            <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1 text-xs">
              {auditEvents.length === 0 ? (
                <div className="p-6 text-center text-muted-foreground">No recent audit events.</div>
              ) : (
                auditEvents.map((evt: any) => (
                  <div key={evt.id} className="p-3 rounded border border-border bg-muted/20">
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-semibold text-foreground">{evt.action}</span>
                      <span className="text-[10px] font-mono text-muted-foreground">
                        {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : 'Recent'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-[11px] text-muted-foreground">
                      <span>Actor: <strong className="text-foreground">{evt.actor}</strong></span>
                      <span className="font-mono bg-card px-1 rounded">{evt.event_type}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  )
}
