import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, ArrowRight } from 'lucide-react'
import { ShimmerButton } from '@/components/ui/ShimmerButton'
import { cn } from '@/lib/utils'

export function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className="fixed top-0 inset-x-0 z-50 flex justify-center px-4 pt-4 sm:pt-6">
      <nav
        className={cn(
          'flex items-center justify-between gap-6 px-4 py-2.5 sm:px-6 sm:py-3 rounded-full transition-all duration-300 max-w-5xl w-full',
          scrolled
            ? 'bg-white/95 backdrop-blur-md border border-slate-200/90 shadow-sm'
            : 'bg-white/85 backdrop-blur-md border border-slate-200/70 shadow-xs',
        )}
      >
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="relative flex size-8 items-center justify-center rounded-xl bg-gradient-to-br from-red-600 to-red-700 text-white shadow-xs">
            <ShieldCheck className="size-4.5" />
            <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-red-400 animate-pulse" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm sm:text-base tracking-tight text-slate-900 group-hover:text-red-600 transition-colors">
                SELLER COPILOT
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-red-50 text-red-700 border border-red-200 font-bold">
                ENTERPRISE
              </span>
            </div>
          </div>
        </Link>

        {/* Center Nav Links */}
        <div className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-600">
          <a
            href="#sandbox"
            className="hover:text-red-600 transition-colors py-1 relative font-medium"
          >
            Live Sandbox
          </a>
          <a
            href="#bento"
            className="hover:text-red-600 transition-colors py-1 relative font-medium"
          >
            Capabilities
          </a>
          <a
            href="#story"
            className="hover:text-red-600 transition-colors py-1 relative font-medium"
          >
            Resolution Flow
          </a>
          <a
            href="#calculator"
            className="hover:text-red-600 transition-colors py-1 relative font-medium"
          >
            ROI Calculator
          </a>
          <a
            href="#telemetry"
            className="hover:text-red-600 transition-colors py-1 relative font-medium"
          >
            Telemetry
          </a>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-3">
          <Link to="/overview">
            <ShimmerButton size="sm" variant="red">
              <span>Launch Dashboard</span>
              <ArrowRight className="size-3.5" />
            </ShimmerButton>
          </Link>
        </div>
      </nav>
    </header>
  )
}
