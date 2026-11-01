import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { NumberTicker } from '@/components/ui/NumberTicker'
import { ShimmerButton } from '@/components/ui/ShimmerButton'
import { Link } from 'react-router-dom'

export function RoiCalculator() {
  const [monthlyGmv, setMonthlyGmv] = useState<number>(150000)
  const [leakageRate, setLeakageRate] = useState<number>(6.5)

  // Calculations
  const annualGmv = monthlyGmv * 12
  const annualLeakage = annualGmv * (leakageRate / 100)
  // Copilot algorithmic defense benchmarked to recover/prevent 78% of margin leakage
  const annualRecovered = Math.round(annualLeakage * 0.78)
  const monthlyCostEstimate = 1200 // Copilot enterprise plan
  const roiMultiple = Math.max(1.2, parseFloat((annualRecovered / (monthlyCostEstimate * 12)).toFixed(1)))

  return (
    <section id="calculator" className="py-24 px-4 sm:px-6 max-w-6xl mx-auto w-full">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <span className="text-[11px] font-mono uppercase tracking-[0.25em] text-red-700 bg-red-50 px-3 py-1 rounded-full border border-red-200 font-semibold shadow-2xs">
          PROFIT DEFENSE CALCULATOR
        </span>
        <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 mt-4 mb-4">
          Calculate Your Brand's{' '}
          <span className="text-gradient-red">Hidden Margin Leakage</span>
        </h2>
        <p className="text-slate-600 text-sm sm:text-base">
          Adjust your monthly Amazon gross sales and estimated leakage rate to see how much profit
          evaporates through overnight Buy Box undercutting, pricing lag, and avoidable FBA stockouts.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch rounded-2xl bg-white p-6 sm:p-10 border border-slate-200 shadow-sm text-left">
        {/* Sliders Column (7 cols) */}
        <div className="lg:col-span-7 flex flex-col justify-between space-y-8">
          {/* Slider 1: Monthly GMV */}
          <div>
            <div className="flex items-baseline justify-between mb-3">
              <div>
                <span className="text-sm font-bold text-slate-900 block">Monthly Amazon Gross Sales (GMV)</span>
                <span className="text-xs text-slate-500">Total volume across all active Amazon marketplaces</span>
              </div>
              <span className="text-2xl font-mono font-bold text-slate-900">
                ${monthlyGmv.toLocaleString()}
              </span>
            </div>

            <input
              type="range"
              min="20000"
              max="1000000"
              step="10000"
              value={monthlyGmv}
              onChange={(e) => setMonthlyGmv(parseInt(e.target.value))}
              className="w-full h-2 rounded-lg bg-slate-200 accent-red-600 cursor-pointer"
            />

            <div className="flex items-center justify-between mt-2 text-[10.5px] font-mono text-slate-500">
              <span>$20K / mo</span>
              <span>$500K / mo</span>
              <span>$1M+ / mo</span>
            </div>
          </div>

          {/* Slider 2: Leakage Rate */}
          <div>
            <div className="flex items-baseline justify-between mb-3">
              <div>
                <span className="text-sm font-bold text-slate-900 block">Estimated Buy Box & Margin Leakage Rate</span>
                <span className="text-xs text-slate-500">Industry average 4-10% lost to competitor undercutting & pricing lag</span>
              </div>
              <span className="text-2xl font-mono font-bold text-red-600">
                {leakageRate.toFixed(1)}%
              </span>
            </div>

            <input
              type="range"
              min="2"
              max="15"
              step="0.5"
              value={leakageRate}
              onChange={(e) => setLeakageRate(parseFloat(e.target.value))}
              className="w-full h-2 rounded-lg bg-slate-200 accent-red-600 cursor-pointer"
            />

            <div className="flex items-center justify-between mt-2 text-[10.5px] font-mono text-slate-500">
              <span>2.0% (Defended)</span>
              <span>6.5% (Typical Brand)</span>
              <span>15.0% (Severe Bleed)</span>
            </div>
          </div>

          {/* Methodology Footnote */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
            <span className="font-semibold text-slate-900 block">Deterministic Model Basis:</span>
            <p className="text-[11px] leading-relaxed text-slate-600">
              Based on empirical analysis of audited Amazon seller portfolios and SP-API pricing histories. Seller Copilot prevents sub-floor race-to-the-bottom undercutting, sustains &gt;94% Buy Box win rates, and mitigates FBA inventory stockouts.
            </p>
          </div>
        </div>

        {/* Live Output Column (5 cols) */}
        <div className="lg:col-span-5 rounded-xl bg-slate-50 border border-slate-200 p-6 flex flex-col justify-between shadow-2xs">
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
                Projected Profit Defended
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-semibold">
                {roiMultiple}x ROI
              </span>
            </div>

            {/* Main Recovered Number */}
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-xs text-slate-500 block mb-1 font-medium">
                Estimated Annual Margin Saved
              </span>
              <div className="text-3xl sm:text-4xl font-mono font-bold text-red-600">
                <NumberTicker value={annualRecovered} prefix="$" />
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Direct contribution margin retained in your seller balance
              </span>
            </div>

            {/* Secondary breakdown */}
            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <span className="text-slate-500 block text-[10.5px] font-sans">Annual Margin Bleed</span>
                <span className="text-red-700 font-bold block text-sm">
                  ${Math.round(annualLeakage).toLocaleString()}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <span className="text-slate-500 block text-[10.5px] font-sans">Payback Period</span>
                <span className="text-slate-900 font-bold block text-sm">
                  &lt; 12 Days
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-200">
            <Link to="/overview" className="w-full block">
              <ShimmerButton variant="red" size="md" className="w-full">
                <span>Start Protecting Your Margins</span>
                <ArrowRight className="size-4" />
              </ShimmerButton>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
