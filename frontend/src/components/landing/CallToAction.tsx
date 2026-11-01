import { Link } from 'react-router-dom'
import { ArrowRight, ShieldCheck, Zap, Lock, Sparkles } from 'lucide-react'
import { ShimmerButton } from '@/components/ui/ShimmerButton'

export function CallToAction() {
  return (
    <section className="py-24 px-4 sm:px-6 max-w-6xl mx-auto w-full">
      <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-red-600 via-red-700 to-red-800 text-white p-8 sm:p-16 text-center shadow-lg border border-red-700">
        {/* Subtle patterned overlay for texture */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(255,255,255,0.4) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        <div className="relative z-10 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/10 border border-white/20 text-white text-xs font-mono uppercase tracking-wider mb-6">
            <Sparkles className="size-3.5 text-red-200" />
            <span>NO SCRAPERS · 100% SP-API & FASTAPI STACK</span>
          </div>

          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white mb-6 leading-tight">
            Deploy Your Brand’s Autonomous Copilot Today
          </h2>

          <p className="text-sm sm:text-lg text-red-100 max-w-2xl mx-auto mb-10 leading-relaxed font-normal">
            Stop losing Buy Box share while you sleep and launching unvalidated products into saturated
            niches. Experience the next era of Amazon seller control.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/overview">
              <ShimmerButton
                size="lg"
                variant="outline"
                className="bg-white text-red-700 hover:bg-red-50 border-white/40 shadow-lg text-base font-bold px-8 py-4"
              >
                <span>Enter The Seller Control Room</span>
                <ArrowRight className="size-5" />
              </ShimmerButton>
            </Link>
          </div>

          {/* Trust Guarantees */}
          <div className="mt-12 pt-8 border-t border-white/15 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs text-red-100 font-mono">
            <span className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-white" />
              SOC2 Type II Compliant
            </span>
            <span className="flex items-center gap-2">
              <Lock className="size-4 text-white" />
              End-to-End Encrypted SP-API
            </span>
            <span className="flex items-center gap-2">
              <Zap className="size-4 text-white" />
              Sub-50ms Reaction Latency
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
