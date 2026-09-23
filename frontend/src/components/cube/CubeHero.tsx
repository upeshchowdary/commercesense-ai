import { animate as fmAnimate, motion, useMotionValue, useReducedMotion } from 'framer-motion'
import { useEffect, useRef } from 'react'

const FACES = [
  { label: 'RESEARCH', sub: 'Gemini + Tavily', transform: 'rotateY(0deg) translateZ(110px)' },
  { label: 'INSIGHT', sub: 'Grounded reasoning', transform: 'rotateY(90deg) translateZ(110px)' },
  { label: 'SIGNAL', sub: 'Deterministic detection', transform: 'rotateY(180deg) translateZ(110px)' },
  { label: 'EVIDENCE', sub: 'Cited sources', transform: 'rotateY(-90deg) translateZ(110px)' },
  { label: 'DECISION', sub: 'Human in the loop', transform: 'rotateX(90deg) translateZ(110px)' },
  { label: 'CUBE', sub: 'AI Commerce Intelligence', transform: 'rotateX(-90deg) translateZ(110px)' },
]

export function CubeHero() {
  const prefersReducedMotion = useReducedMotion()
  const rotateX = useMotionValue(15)
  const rotateY = useMotionValue(-25)
  const stopRef = useRef<() => void>(() => {})

  function spin() {
    if (prefersReducedMotion) return
    // Always resume FROM the current live angle (not a fixed start
    // value) so pausing on hover and letting go never jumps.
    const x = rotateX.get()
    const y = rotateY.get()
    const animX = fmAnimate(rotateX, [x, x + 360], { duration: 28, repeat: Infinity, ease: 'linear' })
    const animY = fmAnimate(rotateY, [y, y + 360], { duration: 36, repeat: Infinity, ease: 'linear' })
    stopRef.current = () => {
      animX.stop()
      animY.stop()
    }
  }

  useEffect(() => {
    spin()
    return () => stopRef.current()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefersReducedMotion])

  return (
    <div
      className="relative mx-auto flex h-[280px] w-[280px] items-center justify-center"
      style={{ perspective: 1000 }}
      onMouseEnter={() => stopRef.current()}
      onMouseLeave={() => spin()}
    >
      <motion.div
        className="relative size-[220px]"
        style={{ transformStyle: 'preserve-3d', rotateX, rotateY }}
      >
        {FACES.map((face) => (
          <div
            key={face.label}
            className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 rounded-2xl border border-border bg-panel shadow-lg backdrop-blur-sm"
            style={{ transform: face.transform }}
          >
            <span className="text-xs font-semibold tracking-[0.2em] text-primary">{face.label}</span>
            <span className="px-4 text-center text-[11px] text-muted-foreground">{face.sub}</span>
          </div>
        ))}
      </motion.div>
      <div
        className="pointer-events-none absolute inset-0 rounded-full opacity-40 blur-3xl"
        style={{
          background:
            'radial-gradient(circle, color-mix(in srgb, var(--blue) 30%, transparent) 0%, transparent 70%)',
        }}
      />
    </div>
  )
}
