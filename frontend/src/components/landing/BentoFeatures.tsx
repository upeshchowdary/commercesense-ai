import { useState } from 'react'
import {
  TrendingUp,
  Cpu,
  Radio,
  Sparkles,
  Search,
  Activity,
  Globe,
  CheckCircle2,
} from 'lucide-react'
import { Card3D } from '@/components/ui/Card3D'
import { NumberTicker } from '@/components/ui/NumberTicker'

export function BentoFeatures() {
  const [imgErrorResearch, setImgErrorResearch] = useState(false)
  const [imgErrorRadar, setImgErrorRadar] = useState(false)

  return (
    <section id="bento" className="py-24 px-4 sm:px-6 max-w-6xl mx-auto w-full">
      {/* Section Header */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-red-50 border border-red-200 text-red-700 text-xs font-mono uppercase tracking-wider mb-4 shadow-2xs">
          <Sparkles className="size-3.5 text-red-600" />
          <span>Autonomous System Capabilities</span>
        </div>
        <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 mb-4">
          Engineered for 7 & 8-Figure{' '}
          <span className="text-gradient-red">Amazon Brands</span>
        </h2>
        <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
          Traditional scrapers only alert you after your margins evaporate. Seller Copilot uses
          multimodal market intelligence and mathematical guardrails to defend and grow every dollar in real time.
        </p>
      </div>

      {/* Bento Grid Layout with Tactile 3D Cards */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 text-left items-stretch">
        {/* Card 1: AI Product Research & ASIN Intelligence (7 cols) */}
        <div className="md:col-span-7 flex flex-col">
          <Card3D
            intensity={10}
            glareOpacity={0.12}
            className="h-full bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-xs hover:border-slate-300 hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="p-2.5 rounded-xl bg-red-50 text-red-600 border border-red-200 shadow-2xs">
                  <Search className="size-6" />
                </div>
                <span className="font-mono text-[11px] text-red-700 bg-red-50 px-2.5 py-1 rounded-full border border-red-200 font-semibold">
                  GEMINI 2.0 FLASH + SEARCH
                </span>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-slate-900 mb-2">
                AI Product Research & ASIN Intelligence
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed mb-5">
                Analyze any Amazon ASIN in seconds. Gemini 2.0 Flash crawls customer review clusters,
                detects unmet competitor feature gaps, and verifies demand velocity with live,
                grounded web search citations.
              </p>

              {/* Research Dossier Visual Viewport */}
              <div className="relative aspect-[16/9] w-full rounded-xl overflow-hidden mb-5 border border-slate-200 bg-slate-900 shadow-inner group/bento">
                {!imgErrorResearch ? (
                  <img
                    src="/images/story/story-act1-research-blindspot.png"
                    alt="AI Product Research Dossier"
                    onError={() => setImgErrorResearch(true)}
                    className="w-full h-full object-cover object-center transition-transform duration-700 group-hover/bento:scale-105"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center bg-slate-900 text-slate-400">
                    <Search className="size-8 text-red-500 mb-2" />
                    <span className="text-xs font-mono">ASIN_INTELLIGENCE_TERMINAL</span>
                  </div>
                )}

                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-slate-950/30 pointer-events-none" />

                {/* Live Scanning Reticle */}
                <div className="absolute inset-x-0 top-1/2 h-0.5 bg-red-500 shadow-[0_0_10px_#DC2626] pointer-events-none" />

                {/* Floating Chips */}
                <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between text-[9.5px] font-mono pointer-events-none">
                  <span className="px-2 py-0.5 rounded-full bg-slate-900/80 backdrop-blur-md text-white border border-white/20">
                    ASIN: B0D1XD1ZV3 (LIVE)
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-red-950/80 backdrop-blur-md text-red-300 border border-red-500/40">
                    MULTIMODAL SYNTHESIS
                  </span>
                </div>

                <div className="absolute bottom-2 left-2.5 right-2.5 flex items-center justify-between text-[10px] font-mono text-slate-300 pointer-events-none">
                  <span className="flex items-center gap-1">
                    <Globe className="size-3 text-red-400" />
                    GOOGLE SEARCH GROUNDING
                  </span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle2 className="size-3" />
                    OPPORTUNITY SCORE 91/100
                  </span>
                </div>
              </div>
            </div>

            {/* Graphic Mock inside Card */}
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 font-mono text-xs space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between text-slate-600 font-medium">
                <span>Niche Analysis Breakdown:</span>
                <span className="text-emerald-700 font-bold flex items-center gap-1">
                  <NumberTicker value={14} /> Competitor Gaps Identified
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-[10.5px]">
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 text-center shadow-2xs">
                  <span className="text-slate-500 block text-[10px]">Review Sentiment</span>
                  <span className="text-emerald-700 font-semibold flex items-center justify-center">
                    <NumberTicker value={94} suffix="%" /> Positive
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 text-center shadow-2xs">
                  <span className="text-slate-500 block text-[10px]">Search Velocity</span>
                  <span className="text-emerald-700 font-semibold">+28% MoM</span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 text-center shadow-2xs">
                  <span className="text-slate-500 block text-[10px]">Web Citations</span>
                  <span className="text-emerald-700 font-semibold">100% Grounded</span>
                </div>
              </div>
            </div>
          </Card3D>
        </div>

        {/* Card 2: Unit Economics Engine (5 cols) */}
        <div className="md:col-span-5 flex flex-col">
          <Card3D
            intensity={10}
            glareOpacity={0.12}
            className="h-full bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-xs hover:border-slate-300 hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="p-2.5 rounded-xl bg-red-50 text-red-600 border border-red-200 shadow-2xs">
                  <TrendingUp className="size-6" />
                </div>
                <span className="font-mono text-[11px] text-red-700 bg-red-50 px-2.5 py-1 rounded-full border border-red-200 font-semibold">
                  PYTHON DECIMAL
                </span>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-slate-900 mb-2">
                Guarded Unit Economics
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed mb-6">
                Zero floating-point inaccuracies. Every pricing calculation strictly enforces
                real-time FBA dimensional fees, 15% referral rates, and TACoS ad spend to defend an inviolable floor.
              </p>
            </div>

            {/* Graphic Mock inside Card */}
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-3 text-xs shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 font-medium">Hard Floor Protection:</span>
                <span className="font-mono text-slate-900 font-bold text-base">
                  <NumberTicker value={24.5} decimals={2} prefix="$" />
                </span>
              </div>
              <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                <div className="bg-red-600 h-full w-[82%]" />
              </div>
              <div className="flex items-center justify-between text-[10.5px] text-slate-500 font-mono">
                <span>Break-even: $24.50</span>
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  Target Margin: <NumberTicker value={28.4} decimals={1} suffix="%" />
                </span>
              </div>
            </div>
          </Card3D>
        </div>

        {/* Card 3: Multi-Agent Consensus Graph (5 cols) */}
        <div className="md:col-span-5 flex flex-col">
          <Card3D
            intensity={10}
            glareOpacity={0.12}
            className="h-full bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-xs hover:border-slate-300 hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="p-2.5 rounded-xl bg-red-50 text-red-600 border border-red-200 shadow-2xs">
                  <Cpu className="size-6" />
                </div>
                <span className="font-mono text-[11px] text-red-700 bg-red-50 px-2.5 py-1 rounded-full border border-red-200 font-semibold">
                  LANGGRAPH MESH
                </span>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-slate-900 mb-2">
                Multi-Agent Autonomous Consensus
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed mb-6">
                Specialized agents for Product Research, Dynamic Pricing, Listing Optimization, and
                FBA Inventory collaborate through structured consensus before submitting actions to SP-API.
              </p>
            </div>

            {/* Mini Pipeline Flow Mock */}
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="flex items-center gap-1.5 text-slate-700 font-semibold">
                  <span className="size-2 rounded-full bg-red-600 animate-pulse" />
                  <NumberTicker value={4} /> Agents Active
                </span>
                <span className="text-slate-500 font-medium">Consensus: 100%</span>
              </div>
              <div className="flex items-center justify-between gap-1 text-[10px] font-mono text-slate-600">
                <div className="p-1.5 rounded-lg bg-white border border-slate-200 flex-1 text-center font-medium shadow-2xs">
                  Research
                </div>
                <span className="text-slate-400">→</span>
                <div className="p-1.5 rounded-lg bg-white border border-slate-200 flex-1 text-center font-medium shadow-2xs">
                  Pricing
                </div>
                <span className="text-slate-400">→</span>
                <div className="p-1.5 rounded-lg bg-white border border-slate-200 flex-1 text-center font-medium shadow-2xs">
                  Listing
                </div>
                <span className="text-slate-400">→</span>
                <div className="p-1.5 rounded-lg bg-red-50 text-red-700 border border-red-200 flex-1 text-center font-bold shadow-2xs">
                  SP-API
                </div>
              </div>
            </div>
          </Card3D>
        </div>

        {/* Card 4: Sub-Second Buy-Box Radar (7 cols) */}
        <div className="md:col-span-7 flex flex-col">
          <Card3D
            intensity={10}
            glareOpacity={0.12}
            className="h-full bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs hover:border-slate-300 hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="p-2.5 rounded-xl bg-red-50 text-red-600 border border-red-200 shadow-2xs">
                  <Radio className="size-6" />
                </div>
                <span className="font-mono text-[11px] text-red-700 bg-red-50 px-2.5 py-1 rounded-full border border-red-200 font-semibold">
                  SUB-SECOND RADAR
                </span>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-slate-900 mb-2">
                Sub-Second Buy Box Radar
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed mb-5">
                Track rival ASIN price cuts, stockout runways, and Buy Box ownership changes.
                Algorithmic countermeasures instantly defend your revenue share without triggering destructive price wars.
              </p>

              {/* Embedded Command Center Image */}
              <div className="relative aspect-[16/9] w-full rounded-xl overflow-hidden mb-5 border border-slate-200 bg-slate-900 shadow-inner group/radar">
                {!imgErrorRadar ? (
                  <img
                    src="/images/story/story-act2-buybox-repricing.png"
                    alt="Algorithmic Repricing Command Center"
                    onError={() => setImgErrorRadar(true)}
                    className="w-full h-full object-cover object-center transition-transform duration-700 group-hover/radar:scale-105"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center bg-slate-900 text-slate-400">
                    <Activity className="size-8 text-red-500 mb-2" />
                    <span className="text-xs font-mono">03:00_AM_COMMAND_DESK</span>
                  </div>
                )}

                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-slate-950/30 pointer-events-none" />

                {/* Glass HUD Telemetry Overlay */}
                <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between text-[9.5px] font-mono pointer-events-none">
                  <span className="px-2 py-0.5 rounded-full bg-slate-900/80 backdrop-blur-md text-white border border-white/20 flex items-center gap-1.5">
                    <span className="size-1.5 rounded-full bg-red-500 animate-ping" />
                    03:17:00 AM EST
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-950/80 backdrop-blur-md text-emerald-300 border border-emerald-500/40">
                    BUY BOX DEFENSE ACTIVE
                  </span>
                </div>

                <div className="absolute bottom-2 left-2.5 right-2.5 flex items-center justify-between text-[10px] font-mono text-slate-200 pointer-events-none">
                  <span>DISPATCHED: 42ms REPRICING MESH</span>
                  <span className="text-emerald-400 font-bold">RESTORED</span>
                </div>
              </div>
            </div>

            {/* Graphic Mock inside Card */}
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-800 font-semibold">Active Buy Box Defense:</span>
                <span className="text-emerald-700 font-bold flex items-center">
                  <NumberTicker value={94.6} decimals={1} suffix="%" /> Win Rate
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-[11px]">
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs">
                  <span className="text-slate-500 block text-[10px]">Competitor Undercut</span>
                  <span className="text-red-600 font-mono font-bold">-$1.50 Detected</span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs">
                  <span className="text-slate-500 block text-[10px]">Autonomous Reaction</span>
                  <span className="text-emerald-700 font-mono font-bold flex items-center gap-1">
                    Countered in <NumberTicker value={118} suffix="ms" />
                  </span>
                </div>
              </div>
            </div>
          </Card3D>
        </div>
      </div>
    </section>
  )
}
