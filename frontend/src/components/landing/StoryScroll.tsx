import { useState, useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import {
  Moon,
  Search,
  Zap,
  Clock,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card3D } from '@/components/ui/Card3D'
import { NumberTicker } from '@/components/ui/NumberTicker'

interface StoryAct {
  step: string
  time: string
  tag: string
  title: string
  icon: typeof Moon
  color: 'amber' | 'rose' | 'emerald'
  image: string
  imageBadge: string
  description: string
  metrics: {
    label: string
    numericValue?: number
    prefix?: string
    suffix?: string
    decimals?: number
    textValue?: string
  }[]
}

const ACTS: StoryAct[] = [
  {
    step: '01',
    time: '11:42 AM EST',
    tag: 'THE CAPITAL SINKHOLE',
    title: 'The Research Blind Spot',
    icon: Search,
    color: 'amber',
    image: '/images/story/story-act1-research-blindspot.png',
    imageBadge: 'UNVALIDATED NICHE LAUNCH DETECTED',
    description:
      'A seller launches a private label product into a seemingly lucrative category without deep competitor gap analysis. Hidden FBA tier size fees, 15% referral overhead, and entrenched rivals turn expected 35% margins into a -$12,400 launch disaster.',
    metrics: [
      { label: 'Capital Burned', numericValue: 12400, prefix: '-$', decimals: 0 },
      { label: 'Competitor Gaps', textValue: 'Missed' },
    ],
  },
  {
    step: '02',
    time: '03:17 AM EST',
    tag: 'THE ALGORITHMIC ATTACK',
    title: 'The 3:00 AM Buy Box Undercut',
    icon: Moon,
    color: 'rose',
    image: '/images/story/story-act2-buybox-repricing.png',
    imageBadge: 'COMPETITOR PRICE WAR INITIATED',
    description:
      'While your team sleeps, an aggressive overseas competitor drops their listing by $3.40. Standard scrapers only poll every 4 to 6 hours. By morning, your sales velocity has collapsed, and thousands in GMV are drained.',
    metrics: [
      { label: 'Lost Buy Box Share', numericValue: 84, prefix: '-', suffix: '%' },
      { label: 'Detection Lag', textValue: '4 hr 18 min' },
    ],
  },
  {
    step: '03',
    time: '03:17:00.042 AM EST',
    tag: 'AUTONOMOUS RESOLUTION',
    title: 'Autonomous Copilot Execution',
    icon: Zap,
    color: 'emerald',
    image: '/images/story/story-act3-copilot-defense.png',
    imageBadge: 'GEMINI MARKET SYNTHESIS ACTIVE',
    description:
      'Within 42 milliseconds, Seller Copilot detects the undercutting event. It matches price within mathematical margin limits, restores 94.6% Buy Box ownership, and leverages Gemini 2.0 Flash to synthesize live market demand without violating your break-even floor.',
    metrics: [
      { label: 'Response Latency', numericValue: 42, suffix: ' ms' },
      { label: 'Buy Box Restored', numericValue: 98, suffix: '%' },
    ],
  },
]

export function StoryScroll() {
  const [activeAct, setActiveAct] = useState(0)
  const [imgErrors, setImgErrors] = useState<Record<string, boolean>>({})
  const containerRef = useRef<HTMLDivElement>(null)

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start end', 'end start'],
  })

  // True 3D Z-depth parallax transforms
  const z0 = useTransform(scrollYProgress, [0, 0.5, 1], [-35, 0, -35])
  const z1 = useTransform(scrollYProgress, [0, 0.5, 1], [-15, 24, -15])
  const z2 = useTransform(scrollYProgress, [0, 0.5, 1], [-35, 0, -35])
  const zTransforms = [z0, z1, z2]

  const y0 = useTransform(scrollYProgress, [0, 0.5, 1], [-18, 0, 18])
  const y1 = useTransform(scrollYProgress, [0, 0.5, 1], [0, 0, 0])
  const y2 = useTransform(scrollYProgress, [0, 0.5, 1], [18, 0, -18])
  const yTransforms = [y0, y1, y2]

  const rotY0 = useTransform(scrollYProgress, [0, 0.5, 1], [3, 0, -3])
  const rotY1 = useTransform(scrollYProgress, [0, 0.5, 1], [0, 0, 0])
  const rotY2 = useTransform(scrollYProgress, [0, 0.5, 1], [-3, 0, 3])
  const rotYTransforms = [rotY0, rotY1, rotY2]

  const handleImageError = (step: string) => {
    setImgErrors((prev) => ({ ...prev, [step]: true }))
  }

  return (
    <section ref={containerRef} id="story" className="py-24 px-4 sm:px-6 max-w-6xl mx-auto w-full">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <span className="text-[11px] font-mono uppercase tracking-[0.25em] text-red-700 bg-red-50 px-3.5 py-1.5 rounded-full border border-red-200 font-semibold shadow-2xs">
          THE SELLER CRISIS & RESOLUTION
        </span>
        <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 mt-5 mb-4">
          How $30,000 Brands Bleed —{' '}
          <span className="text-gradient-red">And How Copilot Solves It</span>
        </h2>
        <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
          From unvalidated product launches to silent 3 AM price wars, see what happens when
          human reaction times are replaced by autonomous multi-agent intelligence.
        </p>
      </div>

      {/* 3-Act Interactive Grid with Framer Motion 3D Z-Depth Parallax */}
      <div
        style={{ perspective: 1200 }}
        className="grid grid-cols-1 lg:grid-cols-3 gap-6 text-left items-stretch"
      >
        {ACTS.map((act, index) => {
          const Icon = act.icon
          const isActive = activeAct === index
          const hasError = imgErrors[act.step]

          return (
            <motion.div
              key={act.step}
              style={{
                z: zTransforms[index],
                y: yTransforms[index],
                rotateY: rotYTransforms[index],
              }}
              className="h-full flex flex-col transform-gpu"
            >
              <Card3D
                intensity={12}
                glareOpacity={0.12}
                onClick={() => setActiveAct(index)}
                className={cn(
                  'h-full rounded-2xl bg-white p-6 sm:p-7 flex flex-col justify-between transition-all duration-300 cursor-pointer border shadow-sm',
                  isActive
                    ? 'border-red-500 ring-2 ring-red-500/20 bg-red-50/10 shadow-md'
                    : 'border-slate-200 hover:border-slate-300 hover:shadow-md',
                )}
              >
                <div>
                  {/* Header row with step and timestamp */}
                  <div className="flex items-center justify-between border-b border-slate-200 pb-4 mb-5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-slate-900">ACT {act.step}</span>
                      <span
                        className={cn(
                          'text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold',
                          act.color === 'rose'
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : act.color === 'amber'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200',
                        )}
                      >
                        {act.tag}
                      </span>
                    </div>
                    <span className="font-mono text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="size-3" />
                      {act.time}
                    </span>
                  </div>

                  {/* Cinematic Industrial Storytelling Image Container */}
                  <div className="relative aspect-[16/10] w-full rounded-xl overflow-hidden mb-5 border border-slate-200/90 bg-slate-900 shadow-inner group/img">
                    {!hasError ? (
                      <img
                        src={act.image}
                        alt={act.title}
                        onError={() => handleImageError(act.step)}
                        className="w-full h-full object-cover object-center transition-transform duration-700 group-hover/img:scale-105"
                      />
                    ) : (
                      /* High-fidelity Tailored SVG Fallback */
                      <div className="w-full h-full flex flex-col items-center justify-center bg-radial from-slate-900 to-slate-950 p-4 text-center select-none relative">
                        <div
                          className="absolute inset-0 opacity-15 pointer-events-none"
                          style={{
                            backgroundImage: 'radial-gradient(circle, #DC2626 1px, transparent 1px)',
                            backgroundSize: '16px 16px',
                          }}
                        />
                        <Icon className="size-8 text-red-500 mb-2 relative z-10 animate-pulse" />
                        <span className="text-xs font-mono text-slate-200 font-bold relative z-10">
                          {act.title}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 mt-1 relative z-10">
                          {act.imageBadge}
                        </span>
                      </div>
                    )}

                    {/* Gradient Overlay for Tag Readability */}
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950/75 via-transparent to-slate-950/40 pointer-events-none" />

                    {/* Top Floating Glass Badge */}
                    <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between pointer-events-none">
                      <span className="text-[9.5px] font-mono px-2 py-0.5 rounded-full bg-slate-900/80 backdrop-blur-md text-white border border-white/20 font-medium">
                        {act.time}
                      </span>
                      <span
                        className={cn(
                          'text-[9px] font-mono px-2 py-0.5 rounded-full backdrop-blur-md border font-semibold',
                          act.color === 'rose'
                            ? 'bg-red-950/80 text-red-300 border-red-500/40'
                            : act.color === 'amber'
                            ? 'bg-amber-950/80 text-amber-300 border-amber-500/40'
                            : 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40',
                        )}
                      >
                        {act.color === 'rose' ? 'VULNERABILITY' : act.color === 'amber' ? 'EXPOSURE' : 'RESOLVED'}
                      </span>
                    </div>

                    {/* Bottom Status Bar over Image */}
                    <div className="absolute bottom-2 left-2.5 right-2.5 flex items-center justify-between text-[10px] font-mono text-slate-200 pointer-events-none">
                      <span className="truncate max-w-[80%] font-medium">{act.imageBadge}</span>
                      {act.color === 'emerald' ? (
                        <CheckCircle2 className="size-3.5 text-emerald-400 shrink-0" />
                      ) : (
                        <AlertTriangle className="size-3.5 text-amber-400 shrink-0" />
                      )}
                    </div>
                  </div>

                  {/* Icon & Title */}
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className={cn(
                        'p-2.5 rounded-xl border shadow-2xs',
                        act.color === 'rose'
                          ? 'bg-red-50 text-red-600 border-red-200'
                          : act.color === 'amber'
                          ? 'bg-amber-50 text-amber-600 border-amber-200'
                          : 'bg-emerald-50 text-emerald-600 border-emerald-200',
                      )}
                    >
                      <Icon className="size-5" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 tracking-tight">{act.title}</h3>
                  </div>

                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed mb-6 font-normal">
                    {act.description}
                  </p>
                </div>

                {/* Metrics Pill Row with Spring NumberTicker */}
                <div className="grid grid-cols-2 gap-2 pt-4 border-t border-slate-200 font-mono">
                  {act.metrics.map((m, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                      <span className="text-[10px] text-slate-500 block font-sans font-medium">{m.label}</span>
                      <span
                        className={cn(
                          'text-sm font-bold flex items-center',
                          act.color === 'emerald'
                            ? 'text-emerald-700'
                            : act.color === 'rose'
                            ? 'text-red-700'
                            : 'text-amber-700',
                        )}
                      >
                        {m.numericValue !== undefined ? (
                          <NumberTicker
                            value={m.numericValue}
                            prefix={m.prefix}
                            suffix={m.suffix}
                            decimals={m.decimals ?? 0}
                          />
                        ) : (
                          m.textValue
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </Card3D>
            </motion.div>
          )
        })}
      </div>
    </section>
  )
}
