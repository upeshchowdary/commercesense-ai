import { useEffect, useRef } from 'react'
import { useInView, useMotionValue, useSpring } from 'framer-motion'
import { cn } from '@/lib/utils'

interface NumberTickerProps {
  value: number
  direction?: 'up' | 'down'
  delay?: number
  className?: string
  decimals?: number
  prefix?: string
  suffix?: string
}

/**
 * Smooth odometer ticker counter for live financial metrics and ROI.
 */
export function NumberTicker({
  value,
  direction = 'up',
  delay = 0,
  className,
  decimals = 0,
  prefix = '',
  suffix = '',
}: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const motionValue = useMotionValue(direction === 'down' ? value : 0)
  const springValue = useSpring(motionValue, {
    damping: 30,
    stiffness: 120,
  })
  const isInView = useInView(ref, { once: true, margin: '0px' })

  useEffect(() => {
    if (isInView) {
      const timer = setTimeout(() => {
        motionValue.set(direction === 'down' ? 0 : value)
      }, delay * 1000)
      return () => clearTimeout(timer)
    }
  }, [motionValue, isInView, delay, value, direction])

  useEffect(() => {
    const format = (latest: number) =>
      `${prefix}${latest.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}${suffix}`

    if (ref.current && !ref.current.textContent) {
      ref.current.textContent = format(direction === 'down' ? value : 0)
    }

    return springValue.on('change', (latest) => {
      if (ref.current) {
        ref.current.textContent = format(latest)
      }
    })
  }, [springValue, decimals, prefix, suffix, direction, value])

  return (
    <span
      ref={ref}
      className={cn('inline-block tabular-nums tracking-tight font-mono', className)}
    />
  )
}
