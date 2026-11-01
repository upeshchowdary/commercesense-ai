import { Check, X, ShieldCheck } from 'lucide-react'

const COMPARISON_ROWS = [
  {
    feature: 'AI Product Research & ASIN Intelligence',
    copilot: 'Gemini 2.0 Flash live competitor gap detection & web search citations',
    traditional: 'Stale keyword volume estimates and delayed CSV exports',
  },
  {
    feature: 'Buy Box Reaction Latency',
    copilot: 'Sub-50 milliseconds via high-concurrency event bus',
    traditional: '4 to 6 hours (Periodic batch scraping)',
  },
  {
    feature: 'Margin Guardrails & Hard Floors',
    copilot: 'Guaranteed Decimal math (Zero floating-point creep, FBA fee aware)',
    traditional: 'Naive rules that trigger destructive race-to-bottom',
  },
  {
    feature: 'Human-in-the-Loop SP-API Execution',
    copilot: '1-click execution queue with automated margin and stockout safety checks',
    traditional: 'Manual copy-pasting adjustments into Seller Central',
  },
  {
    feature: 'Multi-Agent Consensus Graph',
    copilot: 'LangGraph mesh (Research, Pricing, Listing, Inventory consensus)',
    traditional: 'Siloed notification emails with no cross-check',
  },
  {
    feature: 'Data Ingestion Architecture',
    copilot: 'Official Amazon SP-API + GDELT macro radar stream',
    traditional: 'HTML browser scrapers vulnerable to Amazon IP bans',
  },
]

export function ComparisonTable() {
  return (
    <section className="py-24 px-4 sm:px-6 max-w-6xl mx-auto w-full">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <span className="text-[11px] font-mono uppercase tracking-[0.25em] text-red-700 bg-red-50 px-3 py-1 rounded-full border border-red-200 font-semibold shadow-2xs">
          ARCHITECTURAL ADVANTAGE
        </span>
        <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 mt-4 mb-4">
          Legacy Scrapers vs <span className="text-gradient-red">Seller Copilot</span>
        </h2>
        <p className="text-slate-600 text-sm sm:text-base">
          Why leading Amazon aggregators and private label operators are deprecating
          traditional 2018-era tools.
        </p>
      </div>

      <div className="rounded-2xl bg-white border border-slate-200 overflow-x-auto shadow-sm text-left">
        <table className="w-full text-left text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="py-4 px-6 text-slate-600 font-semibold">Capability / Pillar</th>
              <th className="py-4 px-6 text-slate-900 font-bold bg-red-50/50 border-x border-red-200">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-4 text-red-600" />
                  <span className="text-red-700">Seller Copilot Autonomous Engine</span>
                </div>
              </th>
              <th className="py-4 px-6 text-slate-600 font-semibold">
                Legacy Scrapers (Helium 10 / Jungle Scout)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {COMPARISON_ROWS.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                <td className="py-4 px-6 font-semibold text-slate-900">{row.feature}</td>
                <td className="py-4 px-6 bg-red-50/20 border-x border-red-200/60 font-medium text-slate-900">
                  <div className="flex items-start gap-2.5">
                    <Check className="size-4 text-red-600 shrink-0 mt-0.5" />
                    <span>{row.copilot}</span>
                  </div>
                </td>
                <td className="py-4 px-6 text-slate-500">
                  <div className="flex items-start gap-2.5">
                    <X className="size-4 text-slate-400 shrink-0 mt-0.5" />
                    <span>{row.traditional}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
