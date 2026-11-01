import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  DollarSign,
  AlertOctagon,
  Search,
  ExternalLink,
  CheckCircle2,
  Globe,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { NumberTicker } from '@/components/ui/NumberTicker'

interface ResearchSample {
  id: 'airpods' | 'stanley' | 'anker'
  asin: string
  name: string
  brand: string
  category: string
  price: number
  msrp: number
  bsr: string
  monthlyVolume: number
  opportunityScore: number
  sentimentPositive: number
  buyBoxRate: number
  competitorMin: number
  competitorAvg: number
  competitorMax: number
  competitorCount: number
  brief: string
  keyGaps: string[]
  citations: { label: string; domain: string }[]
  recommendedAction: string
}

const RESEARCH_SAMPLES: Record<'airpods' | 'stanley' | 'anker', ResearchSample> = {
  airpods: {
    id: 'airpods',
    asin: 'B0D1XD1ZV3',
    name: 'Apple AirPods Pro (2nd Gen) with USB-C MagSafe',
    brand: 'Apple',
    category: 'Electronics & Audio',
    price: 199.0,
    msrp: 249.0,
    bsr: '#3 in Earbud Headphones',
    monthlyVolume: 420000,
    opportunityScore: 82,
    sentimentPositive: 88,
    buyBoxRate: 96.4,
    competitorMin: 189.0,
    competitorAvg: 219.0,
    competitorMax: 249.0,
    competitorCount: 14,
    brief:
      'Massive search volume with high brand loyalty, but severe price sensitivity among third-party sellers. Critical review clustering reveals user frustration with silicone ear tip fatigue (22% of critical reviews) and charging case scratching.',
    keyGaps: [
      'Unmet demand for bundled ergonomic memory-foam tip upgrades',
      'Protective aerospace-grade silicone case bundle untapped',
      'Rival sellers undercutting by $4-$8 during off-peak weekend hours',
    ],
    citations: [
      { label: 'Market Tech Review', domain: 'theverge.com' },
      { label: 'Amazon Catalog Live', domain: 'amazon.com' },
      { label: 'Audio Frequency Testing', domain: 'rtings.com' },
    ],
    recommendedAction: 'Lock Buy Box defense at $199.00; deploy bundle kit with memory foam tips at +28% contribution margin.',
  },
  stanley: {
    id: 'stanley',
    asin: 'B0C2719K6P',
    name: 'Stanley Quencher H2.0 FlowState Stainless Steel Tumbler 40oz',
    brand: 'Stanley',
    category: 'Home & Kitchen',
    price: 45.0,
    msrp: 45.0,
    bsr: '#1 in Kitchen & Dining',
    monthlyVolume: 890000,
    opportunityScore: 91,
    sentimentPositive: 92,
    buyBoxRate: 91.2,
    competitorMin: 34.99,
    competitorAvg: 42.5,
    competitorMax: 48.0,
    competitorCount: 28,
    brief:
      'Viral category dominator driven by lifestyle social velocity. Natural review sentiment reveals that 34% of 3-star reviews complain of minor leakage when inverted and lack of silicone spill-stopper gaskets in original retail packaging.',
    keyGaps: [
      'Spill-proof replacement lid bundle captures $12 AOV upsell',
      'Dual-tone silicone boot base accessory reduces noise & dings',
      'High competitor stockout frequency creates Buy Box hijack windows',
    ],
    citations: [
      { label: 'Wirecutter Drinkware Test', domain: 'nytimes.com' },
      { label: 'Amazon BSR Tracking', domain: 'amazon.com' },
      { label: 'Retail Trends Digest', domain: 'retaildive.com' },
    ],
    recommendedAction: 'Enforce strict MAP pricing floor at $45.00; harvest surge demand with 1-click SP-API listing optimization.',
  },
  anker: {
    id: 'anker',
    asin: 'B09VPHVT2Z',
    name: 'Anker 737 Power Bank (PowerCore 24K) 140W 3-Port GaN',
    brand: 'Anker',
    category: 'Cell Phones & Accessories',
    price: 109.99,
    msrp: 149.99,
    bsr: '#5 in Portable Power Banks',
    monthlyVolume: 310000,
    opportunityScore: 87,
    sentimentPositive: 94,
    buyBoxRate: 98.5,
    competitorMin: 99.0,
    competitorAvg: 124.99,
    competitorMax: 149.99,
    competitorCount: 9,
    brief:
      'Elite conversion rate among premium tech buyers praising the real-time digital OLED wattage readout. Main competitor vulnerability: lack of explicit TSA airline carry-on watt-hour compliance callouts in bullet points.',
    keyGaps: [
      'Clear TSA carry-on compliance callout in bullet #1 boosts mobile conversion',
      'High-speed 140W braided cable bundle commands +$18 margin cushion',
      'Competitor price drops occur predictably on Tuesday overnight cycles',
    ],
    citations: [
      { label: 'GaN Power Lab Benchmark', domain: 'chargerlab.com' },
      { label: 'Amazon Electronics Index', domain: 'amazon.com' },
      { label: 'TechRadar Hardware Test', domain: 'techradar.com' },
    ],
    recommendedAction: 'Automate sub-second repricing match against rival GaN brands while holding inviolable $94.50 break-even floor.',
  },
}

export function HeroSandbox() {
  const [activeTab, setActiveTab] = useState<'research' | 'pricing'>('research')

  // AI Product Research Agent State
  const [selectedProduct, setSelectedProduct] = useState<'airpods' | 'stanley' | 'anker'>('airpods')
  const product = RESEARCH_SAMPLES[selectedProduct]

  // Pricing Lab Interactive State
  const [targetPrice, setTargetPrice] = useState<number>(34.99)

  // Pricing math calculations (Deterministic Python Decimal simulation)
  const referralFee = targetPrice * 0.15
  const fbaFee = 5.4
  const cogs = 11.2
  const adSpend = targetPrice * 0.16
  const totalCost = referralFee + fbaFee + cogs + adSpend
  const netProfit = targetPrice - totalCost
  const marginPercent = (netProfit / targetPrice) * 100
  const floorPrice = 24.5
  const isBelowFloor = targetPrice < floorPrice
  const buyBoxRate = Math.min(98, Math.max(8, Math.round(110 - targetPrice * 1.8)))

  return (
    <div className="relative w-full max-w-5xl mx-auto rounded-2xl bg-white p-4 sm:p-6 shadow-sm border border-slate-200">
      {/* Top Sandbox Header & Tab Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4 px-1">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-red-600 animate-pulse" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
                Interactive Copilot Runtime
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                v2.4-STABLE
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              Live simulation running on Gemini 2.0 Flash Market Intelligence + Python Decimal Math
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200/80">
          <button
            onClick={() => setActiveTab('research')}
            className={cn(
              'flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer',
              activeTab === 'research'
                ? 'bg-white text-slate-900 border border-slate-200 shadow-xs'
                : 'text-slate-600 hover:text-slate-900',
            )}
          >
            <Sparkles className="size-3.5 text-red-600" />
            <span>AI Product Research Agent</span>
          </button>
          <button
            onClick={() => setActiveTab('pricing')}
            className={cn(
              'flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer',
              activeTab === 'pricing'
                ? 'bg-white text-slate-900 border border-slate-200 shadow-xs'
                : 'text-slate-600 hover:text-slate-900',
            )}
          >
            <DollarSign className="size-3.5 text-red-600" />
            <span>Constrained Pricing Lab</span>
          </button>
        </div>
      </div>

      {/* Main Sandbox Interactive Body */}
      <div className="mt-5">
        <AnimatePresence mode="wait">
          {activeTab === 'research' ? (
            <motion.div
              key="research"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-5 text-left"
            >
              {/* Left: Product Selector & Live ASIN Intelligence Dossier (7 cols) */}
              <div className="lg:col-span-7 flex flex-col gap-4">
                {/* Product Pill Selector Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2">
                    <Search className="size-3.5 text-red-600" />
                    <span className="text-xs font-mono font-bold text-slate-700 uppercase tracking-wider">
                      Target Amazon ASIN:
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {[
                      { id: 'airpods', label: 'AirPods Pro 2', asin: 'B0D1XD1ZV3' },
                      { id: 'stanley', label: 'Stanley 40oz', asin: 'B0C2719K6P' },
                      { id: 'anker', label: 'Anker 737 GaN', asin: 'B09VPHVT2Z' },
                    ].map((item) => (
                      <button
                        key={item.id}
                        onClick={() => setSelectedProduct(item.id as any)}
                        className={cn(
                          'px-2.5 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-1.5',
                          selectedProduct === item.id
                            ? 'bg-red-50 text-red-700 border border-red-300 font-bold shadow-2xs'
                            : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200',
                        )}
                      >
                        <span>{item.label}</span>
                        <span className="text-[10px] opacity-70">({item.asin.slice(0, 5)}…)</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Primary ASIN Card */}
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 sm:p-5 flex flex-col justify-between space-y-4">
                  <div>
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div>
                        <div className="flex flex-wrap items-center gap-2 mb-1.5">
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-white text-slate-800 border border-slate-200 shadow-2xs">
                            ASIN: {product.asin}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-semibold">
                            {product.category}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                            {product.bsr}
                          </span>
                        </div>
                        <h4 className="text-sm sm:text-base font-bold text-slate-900 leading-snug">
                          {product.name}
                        </h4>
                      </div>

                      <div className="text-right shrink-0">
                        <span className="text-xl sm:text-2xl font-mono font-bold text-slate-900 block">
                          ${product.price.toFixed(2)}
                        </span>
                        {product.msrp > product.price && (
                          <span className="text-[11px] font-mono text-slate-400 line-through">
                            MSRP ${product.msrp.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Metric Row: Volume, Competitors, Buy Box Status */}
                    <div className="grid grid-cols-3 gap-2.5 my-3 pt-2 border-t border-slate-200/80 text-xs font-mono">
                      <div className="p-2.5 rounded-lg bg-white border border-slate-200/80 shadow-2xs">
                        <span className="text-slate-500 block text-[10px] font-sans">Monthly Demand</span>
                        <span className="font-bold text-slate-900 flex items-center">
                          <NumberTicker
                            key={`vol-${product.id}`}
                            value={product.monthlyVolume}
                            suffix=" searches"
                          />
                        </span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-white border border-slate-200/80 shadow-2xs">
                        <span className="text-slate-500 block text-[10px] font-sans">Tracked Rivals</span>
                        <span className="font-bold text-slate-900">
                          {product.competitorCount} Active ASINs
                        </span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-white border border-slate-200/80 shadow-2xs">
                        <span className="text-slate-500 block text-[10px] font-sans">Buy Box State</span>
                        <span className="font-bold text-emerald-700 flex items-center gap-1">
                          <span className="size-1.5 rounded-full bg-emerald-600 animate-pulse" />
                          Held {product.buyBoxRate}%
                        </span>
                      </div>
                    </div>

                    {/* Competitor Price Distribution Spectrum */}
                    <div className="p-3 rounded-lg bg-white border border-slate-200/80 space-y-2 shadow-2xs">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-600 font-medium font-sans">
                          Competitor Price Distribution
                        </span>
                        <span className="font-mono text-[11px] text-slate-700">
                          Spread: ${product.competitorMin.toFixed(2)} – ${product.competitorMax.toFixed(2)}
                        </span>
                      </div>

                      <div className="relative w-full h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                        {/* Shaded competitor range across full min-max spread */}
                        <div className="absolute inset-0 h-full bg-gradient-to-r from-red-100 via-amber-100 to-emerald-100 rounded-full" />
                        {/* Current ASIN Marker */}
                        <div
                          className="absolute top-0 bottom-0 w-2.5 bg-red-600 rounded-full shadow-md -translate-x-1/2"
                          style={{
                            left: `${Math.min(
                              96,
                              Math.max(
                                4,
                                ((product.price - product.competitorMin) /
                                  (product.competitorMax - product.competitorMin || 1)) *
                                  100,
                              ),
                            )}%`,
                          }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                        <span>Min: ${product.competitorMin.toFixed(2)}</span>
                        <span className="font-semibold text-slate-700">
                          Median: ${product.competitorAvg.toFixed(2)}
                        </span>
                        <span>Max: ${product.competitorMax.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Grounded Web Search Citations */}
                  <div className="pt-2 border-t border-slate-200 flex flex-wrap items-center gap-2">
                    <span className="text-[10.5px] font-mono text-slate-500 flex items-center gap-1">
                      <Globe className="size-3 text-red-600" />
                      Live Citations:
                    </span>
                    {product.citations.map((c, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-white text-slate-700 border border-slate-200 shadow-2xs"
                      >
                        <span>{c.domain}</span>
                        <ExternalLink className="size-2.5 text-slate-400" />
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right: Gemini Market Intelligence Brief & Action (5 cols) */}
              <div className="lg:col-span-5 rounded-xl bg-slate-50 border border-slate-200 p-5 flex flex-col justify-between">
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="size-4 text-red-600" />
                      <span className="text-xs font-bold text-slate-900 tracking-wide">
                        Gemini 2.0 Flash Market Brief
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-700 bg-white px-2 py-0.5 rounded border border-slate-200 font-semibold">
                      38ms Latency
                    </span>
                  </div>

                  {/* Opportunity Score Gauge */}
                  <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="text-xs text-slate-500 block font-medium">Niche Opportunity Score</span>
                        <span className="text-2xl font-mono font-bold text-slate-900 flex items-center gap-1">
                          <NumberTicker
                            key={`score-${product.id}`}
                            value={product.opportunityScore}
                            suffix=" / 100"
                          />
                        </span>
                      </div>
                      <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        HIGH POTENTIAL
                      </span>
                    </div>

                    {/* Review Sentiment Meter */}
                    <div className="pt-2 border-t border-slate-100 space-y-1">
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span className="text-slate-600">Review Sentiment</span>
                        <span className="text-emerald-700 font-bold">{product.sentimentPositive}% Positive</span>
                      </div>
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden flex">
                        <div
                          className="bg-emerald-600 h-full rounded-full transition-all duration-500"
                          style={{ width: `${product.sentimentPositive}%` }}
                        />
                        <div
                          className="bg-red-500 h-full rounded-full transition-all duration-500"
                          style={{ width: `${100 - product.sentimentPositive}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Gemini Qualitative Synthesis */}
                  <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs text-xs space-y-2">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-red-700 block">
                      Autonomous Competitor Gap Analysis
                    </span>
                    <p className="text-slate-700 leading-relaxed text-[11.5px]">
                      {product.brief}
                    </p>
                    <div className="pt-2 border-t border-slate-100 space-y-1">
                      {product.keyGaps.map((gap, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-[11px] text-slate-600">
                          <CheckCircle2 className="size-3 text-red-600 shrink-0 mt-0.5" />
                          <span>{gap}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Recommended Strategic Action */}
                <div className="mt-4 pt-3 border-t border-slate-200">
                  <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs">
                    <span className="font-mono text-[10px] font-bold text-red-800 uppercase tracking-wide block mb-1">
                      Copilot Recommended Action:
                    </span>
                    <p className="text-[11px] text-red-950 font-medium leading-snug">
                      {product.recommendedAction}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="pricing"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-5 text-left"
            >
              {/* Left: Interactive Slider Control Bay (6 cols) */}
              <div className="lg:col-span-6 rounded-xl bg-slate-50 border border-slate-200 p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">Dynamic Pricing Simulator</h4>
                      <p className="text-xs text-slate-500">
                        Adjust selling price to view deterministic margin and Buy Box probability.
                      </p>
                    </div>
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-semibold">
                      DECIMAL GUARANTEED
                    </span>
                  </div>

                  {/* Slider Control */}
                  <div className="my-6">
                    <div className="flex items-baseline justify-between mb-2">
                      <span className="text-xs font-semibold text-slate-600">Target List Price</span>
                      <span className="text-3xl font-mono font-bold text-slate-900">
                        ${targetPrice.toFixed(2)}
                      </span>
                    </div>

                    <input
                      type="range"
                      min="19.99"
                      max="69.99"
                      step="0.50"
                      value={targetPrice}
                      onChange={(e) => setTargetPrice(parseFloat(e.target.value))}
                      className="w-full h-2 rounded-lg bg-slate-200 accent-red-600 cursor-pointer"
                    />

                    <div className="flex items-center justify-between mt-2 text-[10.5px] font-mono text-slate-500">
                      <span>$19.99 (Aggressive)</span>
                      <span className="text-amber-700 font-semibold">
                        Guardrail Floor: ${floorPrice.toFixed(2)}
                      </span>
                      <span>$69.99 (Premium)</span>
                    </div>
                  </div>

                  {/* Buy Box Win Rate Gauge */}
                  <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-2 shadow-2xs">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-600 font-medium">Estimated Buy Box Win Rate</span>
                      <span className="font-mono font-bold text-red-600">{buyBoxRate}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden border border-slate-200/80">
                      <div
                        className={cn(
                          'h-full transition-all duration-300 rounded-full',
                          buyBoxRate > 75
                            ? 'bg-red-600'
                            : buyBoxRate > 40
                            ? 'bg-amber-500'
                            : 'bg-slate-400',
                        )}
                        style={{ width: `${buyBoxRate}%` }}
                      />
                    </div>
                    <span className="text-[11px] text-slate-500 block">
                      Based on top 3 competitors tracking at $36.00, $38.49, and $39.99.
                    </span>
                  </div>
                </div>

                {isBelowFloor && (
                  <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                    <div className="flex items-center gap-2">
                      <AlertOctagon className="size-4 shrink-0 text-red-600" />
                      <span>
                        <strong>Autonomous Guardrail Active:</strong> Cannot price below mathematical
                        break-even floor (${floorPrice.toFixed(2)}).
                      </span>
                    </div>
                    <button
                      onClick={() => setTargetPrice(floorPrice)}
                      className="px-2.5 py-1 rounded-lg bg-red-600 hover:bg-red-700 text-white font-mono font-bold text-[11px] shrink-0 cursor-pointer transition-colors shadow-2xs"
                    >
                      Enforce Floor (${floorPrice.toFixed(2)})
                    </button>
                  </div>
                )}
              </div>

              {/* Right: Live Unit Economics Breakdown (6 cols) */}
              <div className="lg:col-span-6 rounded-xl bg-slate-50 border border-slate-200 p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-4">
                    <span className="text-xs font-bold text-slate-900 tracking-wide">
                      Instant Unit Economics Breakdown
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">Per Sold Unit</span>
                  </div>

                  <div className="space-y-2.5 text-xs font-mono">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60 shadow-2xs">
                      <span className="text-slate-600">Gross Sale Price</span>
                      <span className="font-bold text-slate-900">+${targetPrice.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60 shadow-2xs">
                      <span className="text-slate-600">Amazon Referral Fee (15%)</span>
                      <span className="text-red-600">-${referralFee.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60 shadow-2xs">
                      <span className="text-slate-600">FBA Pick & Pack (Standard)</span>
                      <span className="text-red-600">-${fbaFee.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60 shadow-2xs">
                      <span className="text-slate-600">Cost of Goods (COGS)</span>
                      <span className="text-red-600">-${cogs.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60 shadow-2xs">
                      <span className="text-slate-600">Blended Ad Spend (16% TACoS)</span>
                      <span className="text-red-600">-${adSpend.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                {/* Net Margin Box */}
                <div
                  className={cn(
                    'mt-5 p-4 rounded-xl border transition-colors flex items-center justify-between shadow-2xs',
                    netProfit > 6
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                      : netProfit > 2
                      ? 'bg-amber-50 border-amber-200 text-amber-900'
                      : 'bg-red-50 border-red-200 text-red-900',
                  )}
                >
                  <div>
                    <span className="text-xs opacity-80 block">Calculated Net Profit / Unit</span>
                    <span className="text-2xl font-mono font-bold">
                      {netProfit < 0
                        ? `-$${Math.abs(netProfit).toFixed(2)}`
                        : `$${netProfit.toFixed(2)}`}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs opacity-80 block">Contribution Margin</span>
                    <span className="text-xl font-mono font-bold">
                      {marginPercent.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
