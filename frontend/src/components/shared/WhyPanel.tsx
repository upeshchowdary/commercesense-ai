// "Why does this matter?" (spec §35) and "Why not? / Alternatives
// considered" (spec §36) panels. Collapsed by default so they don't
// dominate every card; every field is sourced from data the caller
// already computed deterministically — nothing here invents a claim.
import { ChevronDown, HelpCircle, Scale } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

interface WhyPanelProps {
  what: string
  why: string
  evidence: string
  calculation: string
  ifNothing: string
  proposedAction: string
  missingInfo?: string
}

export function WhyPanel({ what, why, evidence, calculation, ifNothing, proposedAction, missingInfo }: WhyPanelProps) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-lg border border-border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="flex items-center gap-1.5">
          <HelpCircle className="size-3.5" /> Why does this matter?
        </span>
        <ChevronDown className={cn('size-3.5 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <dl className="flex flex-col gap-2 border-t border-border px-3 py-3 text-xs">
          <Row term="What happened?" value={what} />
          <Row term="Why does it matter?" value={why} />
          <Row term="Evidence" value={evidence} />
          <Row term="Calculation" value={calculation} />
          <Row term="If we do nothing" value={ifNothing} />
          <Row term="Proposed next action" value={proposedAction} />
          <Row term="What's missing" value={missingInfo ?? 'Nothing known to be missing from this analysis.'} />
        </dl>
      )}
    </div>
  )
}

function Row({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="font-medium text-foreground">{term}</dt>
      <dd className="text-muted-foreground">{value}</dd>
    </div>
  )
}

interface AlternativeOption {
  label: string
  detail: string
}

export function AlternativesPanel({ options }: { options: AlternativeOption[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-lg border border-border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="flex items-center gap-1.5">
          <Scale className="size-3.5" /> Why not? Alternatives considered
        </span>
        <ChevronDown className={cn('size-3.5 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="flex flex-col gap-2 border-t border-border px-3 py-3 text-xs">
          <p className="text-muted-foreground">
            This is decision support, not autonomous decision-making — none of these is guaranteed optimal.
          </p>
          {options.map((o, i) => (
            <div key={i} className="rounded-md border border-border/60 p-2">
              <p className="font-medium text-foreground">{o.label}</p>
              <p className="mt-0.5 text-muted-foreground">{o.detail}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
