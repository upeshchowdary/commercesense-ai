import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { getAutomationRules, patchAutomationRule, postEvaluateAutomations } from '@/lib/api'
import {
  Zap,
  Clock,
  ShieldCheck,
  Sliders,
  RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Automations() {
  const queryClient = useQueryClient()
  const [evaluating, setEvaluating] = useState(false)
  const [evalResult, setEvalResult] = useState<string | null>(null)

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ['automation_rules'],
    queryFn: getAutomationRules,
  })

  const toggleMutation = useMutation({
    mutationFn: ({ ruleId, enabled }: { ruleId: number; enabled: boolean }) =>
      patchAutomationRule(ruleId, { enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['automation_rules'] }),
  })

  const cooldownMutation = useMutation({
    mutationFn: ({ ruleId, cooldown_hours }: { ruleId: number; cooldown_hours: number }) =>
      patchAutomationRule(ruleId, { cooldown_hours }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['automation_rules'] }),
  })

  const evaluateMutation = useMutation({
    mutationFn: postEvaluateAutomations,
    onMutate: () => {
      setEvaluating(true)
      setEvalResult(null)
    },
    onSuccess: (res) => {
      setEvaluating(false)
      setEvalResult(`Catalog scan finished: generated ${res.new_actions_count} new action drafts.`)
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
    onError: () => {
      setEvaluating(false)
      setEvalResult('Evaluation failed.')
    },
  })

  return (
    <AppShell>
      <Topbar
        title="Automations & Rules"
        actions={
          <Button
            size="sm"
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluating}
            className="gap-1.5 bg-red-600 hover:bg-red-700 text-white shadow-xs"
          >
            <RefreshCw className={cn('size-3.5', evaluating && 'animate-spin')} />
            <span>Scan Catalog Now</span>
          </Button>
        }
      />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Banner */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Automated Sentinel & Policy Rules
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Active scanners identify catalog exceptions, margin breaches, and stockout hazards. All triggers route to the Action Center for operator confirmation.
            </p>
          </div>
          <ProvenanceBadge provenance="CALCULATED" />
        </div>

        {evalResult && (
          <div className="mb-6 p-3.5 rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950/40 text-xs font-medium text-blue-800 dark:text-blue-300 flex items-center justify-between">
            <span>{evalResult}</span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => (window.location.href = '/actions')}
              className="h-7 text-xs bg-white dark:bg-card"
            >
              View in Action Center →
            </Button>
          </div>
        )}

        {/* Rules Grid */}
        <div className="grid grid-cols-1 gap-4">
          {isLoading ? (
            <div className="h-48 rounded-lg border border-border bg-card animate-pulse" />
          ) : (
            rules.map((rule) => (
              <div
                key={rule.id}
                className={cn(
                  'rounded-lg border p-5 bg-card transition-all flex flex-col md:flex-row md:items-center justify-between gap-4',
                  rule.enabled ? 'border-border' : 'border-border/50 opacity-60 bg-muted/20',
                )}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'size-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5',
                      rule.enabled ? 'bg-red-50 text-red-600 border border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900/50' : 'bg-muted text-muted-foreground',
                    )}
                  >
                    <Zap className="size-4.5" />
                  </div>

                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                        {rule.name}
                      </span>
                      <span className="font-mono text-[10.5px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                        {rule.rule_type}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-slate-600 dark:text-slate-400 mt-1.5 flex-wrap">
                      <div className="flex items-center gap-1.5">
                        <Clock className="size-3.5" />
                        <span>Cooldown:</span>
                        <select
                          value={rule.cooldown_hours}
                          onChange={(e) =>
                            cooldownMutation.mutate({ ruleId: rule.id, cooldown_hours: Number(e.target.value) })
                          }
                          className="border border-border rounded px-1.5 py-0.5 text-[11px] bg-card text-foreground"
                        >
                          <option value={12}>12 Hours</option>
                          <option value={24}>24 Hours</option>
                          <option value={48}>48 Hours</option>
                          <option value={72}>72 Hours</option>
                        </select>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Sliders className="size-3.5" />
                        <span>Condition:</span>
                        <span className="font-mono text-[11px] bg-muted/40 px-1 rounded">
                          {JSON.stringify(rule.condition_json)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Toggle */}
                <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                  <span className="text-xs font-medium text-muted-foreground">
                    {rule.enabled ? 'Active' : 'Paused'}
                  </span>
                  <button
                    type="button"
                    onClick={() => toggleMutation.mutate({ ruleId: rule.id, enabled: !rule.enabled })}
                    className={cn(
                      'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden',
                      rule.enabled ? 'bg-red-600' : 'bg-slate-200 dark:bg-slate-700',
                    )}
                  >
                    <span
                      className={cn(
                        'pointer-events-none inline-block size-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out',
                        rule.enabled ? 'translate-x-5' : 'translate-x-0',
                      )}
                    />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Operational Guardrail Notice */}
        <div className="mt-8 p-4 rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 shadow-xs text-xs text-slate-800 dark:text-slate-200">
          <div className="flex items-center gap-2 font-semibold text-red-600 dark:text-red-400 mb-1">
            <ShieldCheck className="size-4" />
            <span>Strict Human-in-the-Loop Guardrail (Spec §17-18)</span>
          </div>
          <p className="text-slate-600 dark:text-slate-400">
            CommerceSense AI never writes autonomous changes to Amazon retail listings or pricing. Rules draft candidate adjustments directly into the Action Center where sellers maintain final approval authority.
          </p>
        </div>
      </main>
    </AppShell>
  )
}
