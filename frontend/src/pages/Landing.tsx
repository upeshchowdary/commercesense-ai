import { Link } from 'react-router-dom'
import {
  ArrowRight,
  ShieldCheck,
  ChevronDown,
} from 'lucide-react'
import { LandingNavbar } from '@/components/landing/LandingNavbar'
import { HeroSandbox } from '@/components/landing/HeroSandbox'
import { LogoMarquee } from '@/components/landing/LogoMarquee'
import { BentoFeatures } from '@/components/landing/BentoFeatures'
import { StoryScroll } from '@/components/landing/StoryScroll'
import { RoiCalculator } from '@/components/landing/RoiCalculator'
import { AgentTerminal } from '@/components/landing/AgentTerminal'
import { ComparisonTable } from '@/components/landing/ComparisonTable'
import { CallToAction } from '@/components/landing/CallToAction'
import { ShimmerButton } from '@/components/ui/ShimmerButton'

export default function Landing() {
  return (
    <div className="relative min-h-screen bg-[#F8FAFC] text-slate-900 selection:bg-red-500/20 selection:text-red-900 overflow-hidden font-sans">
      {/* Subtle Engineering Dot Grid */}
      <div className="pointer-events-none absolute inset-0 bg-tech-grid opacity-40" />

      {/* Floating Dynamic Island Navbar */}
      <LandingNavbar />

      {/* Hero Section */}
      <section className="relative pt-32 sm:pt-40 pb-20 px-4 sm:px-6 max-w-6xl mx-auto flex flex-col items-center text-center">
        {/* Release Tag */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-mono mb-8 shadow-xs hover:border-red-300 transition-colors cursor-default">
          <span className="size-2 rounded-full bg-red-600 animate-pulse" />
          <span className="text-slate-600 font-medium">GEMINI 2.0 FLASH MULTIMODAL RUNTIME</span>
          <span className="text-red-600 font-bold">LIVE v2.4</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-900 max-w-4xl leading-[1.1] mb-6">
          The Autonomous Amazon Copilot That{' '}
          <span className="text-gradient-red">Defends Every Cent.</span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-sm sm:text-lg text-slate-600 max-w-2xl mx-auto mb-10 leading-relaxed font-normal">
          Stop losing Buy Box share at 3:00 AM and launching unvalidated products into saturated niches.
          Seller Copilot fuses live Gemini market intelligence with mathematical margin guardrails to
          scale and defend your brand around the clock.
        </p>

        {/* Hero Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-16">
          <Link to="/overview">
            <ShimmerButton size="lg" variant="red">
              <span>Launch Seller Control Room</span>
              <ArrowRight className="size-5" />
            </ShimmerButton>
          </Link>
          <a href="#sandbox">
            <ShimmerButton size="lg" variant="outline">
              <span>Test Interactive Sandbox</span>
              <ChevronDown className="size-4" />
            </ShimmerButton>
          </a>
        </div>

        {/* Interactive Live Hero Sandbox */}
        <div id="sandbox" className="w-full pt-4">
          <HeroSandbox />
        </div>
      </section>

      {/* Ecosystem Logo Marquee */}
      <LogoMarquee />

      {/* 4-Pillar Bento Grid */}
      <BentoFeatures />

      {/* 3-Act Storytelling Scroll */}
      <StoryScroll />

      {/* Interactive ROI & Profit Calculator */}
      <RoiCalculator />

      {/* Live Agent Telemetry Console */}
      <AgentTerminal />

      {/* Comparison Matrix */}
      <ComparisonTable />

      {/* Conversion CTA */}
      <CallToAction />

      {/* Engineered High-Craft Footer */}
      <footer className="border-t border-slate-200 bg-white py-14 px-4 sm:px-6 relative z-10">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-slate-600 font-mono">
          <div className="flex items-center gap-3">
            <div className="flex size-7 items-center justify-center rounded-lg bg-red-50 text-red-600 border border-red-200 shadow-2xs">
              <ShieldCheck className="size-4" />
            </div>
            <div>
              <span className="text-slate-900 font-bold block">SELLER COPILOT // COMMERCESENSE</span>
              <span className="text-slate-500 text-[10px]">Autonomous Amazon Seller Operating System</span>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <Link to="/overview" className="hover:text-red-600 transition-colors">
              Control Room
            </Link>
            <Link to="/research" className="hover:text-red-600 transition-colors">
              Research Agent
            </Link>
            <Link to="/pricing-lab" className="hover:text-red-600 transition-colors">
              Pricing Lab
            </Link>
            <Link to="/competitors" className="hover:text-red-600 transition-colors">
              Competitor Watch
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-500" />
            <span className="text-slate-600">All Systems Nominal · 163 Tests Passing</span>
          </div>
        </div>

        <div className="max-w-6xl mx-auto mt-8 pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>© 2026 Seller Copilot Commerce Intelligence. Engineered for elite brand operators.</span>
          <span>SP-API Integrated · Gemini 2.0 Flash Powered</span>
        </div>
      </footer>
    </div>
  )
}
