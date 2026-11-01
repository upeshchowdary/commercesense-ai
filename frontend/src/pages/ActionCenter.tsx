import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { getActions, postDecideAction, postEvaluateAutomations } from '@/lib/api'
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Scale,
  ShieldAlert,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function ActionCenter() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'QUEUED' | 'APPROVED' | 'REJECTED' | 'SNOOZED' | 'ALL'>('QUEUED')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  // Decision Modal State
  const [decisionModal, setDecisionModal] = useState<{
    open: boolean
    actionId: number | null
    type: 'APPROVED' | 'REJECTED' | 'SNOOZED'
    actionTitle: string
  }>({
    open: false,
    actionId: null,
    type: 'APPROVED',
    actionTitle: '',
  })
  const [reasonInput, setReasonInput] = useState('')
  const [snoozeDays, setSnoozeDays] = useState(7)

  // Fetch actions
  const { data: actions = [], isLoading } = useQuery({
    queryKey: ['actions', activeTab === 'ALL' ? undefined : activeTab],
    queryFn: () => getActions(activeTab === 'ALL' ? undefined : { status: activeTab }),
  })

  // Mutations
  const decideMutation = useMutation({
    mutationFn: ({
      actionId,
      decision,
      reason,
      snooze,
    }: {
      actionId: number
      decision: 'APPROVED' | 'REJECTED' | 'SNOOZED'
      reason?: string
      snooze?: number
    }) => postDecideAction(actionId, decision, reason, snooze),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
      setDecisionModal({ open: false, actionId: null, type: 'APPROVED', actionTitle: '' })
      setReasonInput('')
    },
  })

  const evaluateMutation = useMutation({
    mutationFn: postEvaluateAutomations,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })

  const openDecision = (actionId: number, type: 'APPROVED' | 'REJECTED' | 'SNOOZED', title: string) => {
    setDecisionModal({ open: true, actionId, type, actionTitle: title })
    setReasonInput('')
  }

  const handleConfirmDecision = () => {
    if (!decisionModal.actionId) return
    decideMutation.mutate({
      actionId: decisionModal.actionId,
      decision: decisionModal.type,
      reason: reasonInput,
      snooze: decisionModal.type === 'SNOOZED' ? snoozeDays : undefined,
    })
  }

  const counts = {
    QUEUED: actions.filter((a) => a.status === 'QUEUED').length,
    APPROVED: actions.filter((a) => a.status === 'APPROVED').length,
    REJECTED: actions.filter((a) => a.status === 'REJECTED').length,
    SNOOZED: actions.filter((a) => a.status === 'SNOOZED').length,
  }

  return (
    <AppShell>
      <Topbar
        title="Action Center"
        actions={
          <Button
            size="sm"
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluateMutation.isPending}
            className="gap-1.5 bg-red-600 hover:bg-red-700 text-white shadow-xs"
          >
            <RefreshCw className={cn('size-3.5', evaluateMutation.isPending && 'animate-spin')} />
            <span>Evaluate Rules</span>
          </Button>
        }
      />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header Summary */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Human-in-the-Loop Operations Inbox
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Zero autonomous account modifications. Every price shift, replenishment order, or listing update drafts here for operator review.
            </p>
          </div>
          <ProvenanceBadge provenance="CALCULATED" />
        </div>

        {/* Tab Filters */}
        <div className="flex items-center gap-2 border-b border-border mb-6 overflow-x-auto pb-px">
          {(['QUEUED', 'APPROVED', 'REJECTED', 'SNOOZED', 'ALL'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'flex items-center gap-2 px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap',
                activeTab === tab
                  ? 'border-red-600 text-red-700 dark:border-red-500 dark:text-red-400'
                  : 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400',
              )}
            >
              <span>{tab === 'QUEUED' ? 'Pending Approval' : tab.charAt(0) + tab.slice(1).toLowerCase()}</span>
              {tab === 'QUEUED' && counts.QUEUED > 0 && (
                <span className="rounded-full bg-red-600 px-1.5 py-0.2 text-[10px] text-white font-bold">
                  {counts.QUEUED}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Actions List */}
        {isLoading ? (
          <div className="flex flex-col gap-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-28 rounded-lg border border-border bg-card animate-pulse" />
            ))}
          </div>
        ) : actions.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-center rounded-xl border border-dashed border-border bg-card">
            <div className="size-12 rounded-full bg-red-50 dark:bg-red-950/40 flex items-center justify-center text-red-600 mb-3">
              <CheckCircle2 className="size-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Inbox Zero</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 max-w-md">
              No actions currently matching "{activeTab}". Click "Evaluate Rules" to run the catalog scanner against active thresholds.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3.5">
            {actions.map((item) => {
              const isExpanded = expandedId === item.id
              const why = item.why_panel || {}

              return (
                <div
                  key={item.id}
                  className="rounded-lg border border-border bg-card transition-shadow hover:shadow-xs overflow-hidden"
                >
                  {/* Card Header Row */}
                  <div className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="flex items-start gap-3.5 min-w-0">
                      <div
                        className={cn(
                          'mt-0.5 size-8 rounded-md flex items-center justify-center shrink-0',
                          item.action_type === 'PRICE_ADJUSTMENT' && 'bg-[#EAF2F8] text-[#2B6CB0]',
                          item.action_type === 'REORDER_INVENTORY' && 'bg-[#FEFCBF] text-[#744210]',
                          item.action_type === 'PRICE_FLOOR_DEFENSE' && 'bg-[#FBECEC] text-[#C84B4B]',
                          item.action_type === 'REVIEW_DEFENSE' && 'bg-[#FAF5FF] text-[#6B46C1]',
                          item.action_type === 'LIQUIDATE_OR_DISCOUNT' && 'bg-[#FEEBC8] text-[#C05621]',
                        )}
                      >
                        {item.action_type === 'PRICE_FLOOR_DEFENSE' ? (
                          <ShieldAlert className="size-4" />
                        ) : item.action_type === 'REORDER_INVENTORY' ? (
                          <Inbox className="size-4" />
                        ) : (
                          <AlertTriangle className="size-4" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                            {item.action_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-muted-foreground">·</span>
                          <span className="text-xs font-medium text-slate-900 dark:text-slate-100">
                            {item.product_name}
                          </span>
                          {item.asin && (
                            <span className="font-mono text-[11px] text-slate-600 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                              {item.asin}
                            </span>
                          )}
                          <ProvenanceBadge provenance="CALCULATED" className="text-[10px] py-0" />
                        </div>

                        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                          {item.title}
                        </h3>
                        <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 line-clamp-2">
                          {item.description}
                        </p>
                      </div>
                    </div>

                    {/* Actions and Status */}
                    <div className="flex items-center gap-2 shrink-0 self-end lg:self-center">
                      {item.status === 'QUEUED' ? (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openDecision(item.id, 'SNOOZED', item.title)}
                            className="text-xs h-8 text-slate-600"
                          >
                            <Clock className="size-3.5 mr-1" />
                            Snooze
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openDecision(item.id, 'REJECTED', item.title)}
                            className="text-xs h-8 text-red-600 border-red-200 hover:bg-red-50"
                          >
                            <XCircle className="size-3.5 mr-1" />
                            Reject
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => openDecision(item.id, 'APPROVED', item.title)}
                            className="text-xs h-8 bg-red-600 hover:bg-red-700 text-white shadow-xs"
                          >
                            <CheckCircle2 className="size-3.5 mr-1" />
                            Approve
                          </Button>
                        </>
                      ) : (
                        <span
                          className={cn(
                            'px-2.5 py-1 rounded text-xs font-semibold uppercase tracking-wider',
                            item.status === 'APPROVED' && 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400',
                            item.status === 'REJECTED' && 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400',
                            item.status === 'SNOOZED' && 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400',
                          )}
                        >
                          {item.status}
                        </span>
                      )}

                      <button
                        onClick={() => setExpandedId(isExpanded ? null : item.id)}
                        className="p-1.5 rounded hover:bg-muted text-slate-600 transition-colors ml-1"
                        aria-label="Toggle Why Panel"
                      >
                        {isExpanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Expandable Why Panel */}
                  {isExpanded && (
                    <div className="border-t border-border bg-slate-50 dark:bg-slate-900 p-4 text-xs flex flex-col gap-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-1">
                            Financial Impact at Current Volume
                          </span>
                          <p className="text-muted-foreground bg-card border border-border p-2.5 rounded">
                            {why.financial_impact_at_current_volume || 'No volume elasticity fabricated.'}
                          </p>
                        </div>

                        <div>
                          <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-1">
                            Evidence & Metrics
                          </span>
                          <div className="bg-card border border-border p-2.5 rounded space-y-1 font-mono text-[11px]">
                            {why.evidence &&
                              Object.entries(why.evidence).map(([k, v]) => (
                                <div key={k} className="flex justify-between">
                                  <span className="text-muted-foreground">{k}:</span>
                                  <span className="text-foreground font-semibold">{String(v)}</span>
                                </div>
                              ))}
                          </div>
                        </div>
                      </div>

                      {/* Alternatives Considered */}
                      {why.alternatives_considered && why.alternatives_considered.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 font-semibold text-slate-900 dark:text-slate-100 mb-1">
                            <Scale className="size-3.5" />
                            <span>Alternatives Evaluated</span>
                          </div>
                          <ul className="list-disc list-inside space-y-1 text-muted-foreground bg-card border border-border p-2.5 rounded">
                            {why.alternatives_considered.map((alt: string, idx: number) => (
                              <li key={idx}>{alt}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </main>

      {/* Decision Confirmation Dialog */}
      <Dialog open={decisionModal.open} onOpenChange={(o) => setDecisionModal((s) => ({ ...s, open: o }))}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Confirm {decisionModal.type} Action
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <p className="font-medium text-slate-900 dark:text-slate-100">{decisionModal.actionTitle}</p>

            {decisionModal.type === 'SNOOZED' && (
              <div>
                <label className="block font-semibold mb-1">Snooze Duration (Days):</label>
                <select
                  value={snoozeDays}
                  onChange={(e) => setSnoozeDays(Number(e.target.value))}
                  className="w-full border border-border rounded px-2.5 py-1.5 bg-card text-foreground"
                >
                  <option value={3}>3 Days</option>
                  <option value={7}>7 Days (Standard)</option>
                  <option value={14}>14 Days</option>
                  <option value={30}>30 Days</option>
                </select>
              </div>
            )}

            <div>
              <label className="block font-semibold mb-1">
                Operator Notes / Reason {decisionModal.type === 'REJECTED' && <span className="text-red-500">*</span>}:
              </label>
              <textarea
                value={reasonInput}
                onChange={(e) => setReasonInput(e.target.value)}
                placeholder={
                  decisionModal.type === 'REJECTED'
                    ? 'State required operational justification for rejection...'
                    : 'Optional operator notes for audit trail...'
                }
                rows={3}
                className="w-full border border-border rounded p-2 bg-card text-foreground"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDecisionModal((s) => ({ ...s, open: false }))}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={decisionModal.type === 'REJECTED' && !reasonInput.trim()}
              onClick={handleConfirmDecision}
              className={cn(
                'text-white',
                decisionModal.type === 'APPROVED' && 'bg-emerald-600 hover:bg-emerald-700',
                decisionModal.type === 'REJECTED' && 'bg-red-600 hover:bg-red-700',
                decisionModal.type === 'SNOOZED' && 'bg-amber-600 hover:bg-amber-700',
              )}
            >
              Confirm {decisionModal.type}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
