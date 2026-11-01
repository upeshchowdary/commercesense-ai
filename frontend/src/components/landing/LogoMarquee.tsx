import {
  Boxes,
  Database,
  Globe2,
  Lock,
  Layers,
  Sparkles,
  Zap,
} from 'lucide-react'

const ENGINES = [
  { name: 'Amazon SP-API v2024', tag: 'Direct Ingestion', icon: Globe2 },
  { name: 'Gemini 2.0 Flash', tag: 'Market Intelligence', icon: Sparkles },
  { name: 'Walmart Marketplace', tag: 'Omnichannel Feed', icon: Boxes },
  { name: 'Google Search Grounding', tag: 'Live Web Citations', icon: Globe2 },
  { name: 'PostgreSQL 16 pgvector', tag: 'Catalog Memory', icon: Database },
  { name: 'Python Decimal Engine', tag: 'Guarded Unit Economics', icon: Lock },
  { name: 'LangGraph Consensus', tag: 'Multi-Agent Mesh', icon: Layers },
  { name: 'FastAPI High-Concurrency', tag: 'Sub-40ms Telemetry', icon: Zap },
]

export function LogoMarquee() {
  return (
    <div className="relative w-full overflow-hidden py-10 border-y border-slate-200 bg-white/80">
      <div className="text-center mb-6">
        <span className="text-[11px] font-mono uppercase tracking-[0.25em] text-slate-500 font-semibold">
          ENTERPRISE AMAZON SELLER INTELLIGENCE & COPILOT STACK
        </span>
      </div>

      {/* Fade Gradients at Edges */}
      <div className="pointer-events-none absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-[#F8FAFC] to-transparent z-10" />
      <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-[#F8FAFC] to-transparent z-10" />

      {/* Infinite Scrolling Track */}
      <div className="flex animate-marquee">
        {[...ENGINES, ...ENGINES].map((engine, idx) => {
          const Icon = engine.icon
          return (
            <div
              key={idx}
              className="flex items-center gap-3 mx-4 px-4 py-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs hover:border-red-300 hover:shadow-xs transition-all group shrink-0"
            >
              <div className="p-1.5 rounded-lg bg-slate-50 text-slate-500 group-hover:text-red-600 group-hover:bg-red-50 transition-colors">
                <Icon className="size-4" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-800 group-hover:text-red-700 transition-colors">
                  {engine.name}
                </span>
                <span className="text-[10px] font-mono text-slate-500 group-hover:text-red-600 transition-colors">
                  {engine.tag}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
