import { useRef, useState, useCallback, type HTMLAttributes, type ReactNode, type MouseEvent } from 'react'
import { motion, useSpring, useTransform } from 'framer-motion'
import { cn } from '@/lib/utils'

interface SpotlightProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode
  className?: string
  fill?: string
  size?: number
  opacity?: number
}

/**
 * Flashlight cursor tracking radial illumination across dark surfaces.
 */
export function Spotlight({
  children,
  className,
  fill = 'rgba(16, 185, 129, 0.14)',
  size = 380,
  opacity = 0.8,
  ...props
}: SpotlightProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isHovered, setIsHovered] = useState(false)

  const mouseX = useSpring(0, { stiffness: 350, damping: 28 })
  const mouseY = useSpring(0, { stiffness: 350, damping: 28 })

  const handleMouseMove = useCallback(
    (e: MouseEvent<HTMLDivElement>) => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      mouseX.set(e.clientX - rect.left)
      mouseY.set(e.clientY - rect.top)
    },
    [mouseX, mouseY],
  )

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn('relative overflow-hidden', className)}
      {...props}
    >
      <motion.div
        className="pointer-events-none absolute -inset-px transition-opacity duration-300"
        style={{
          opacity: isHovered ? opacity : 0,
          background: useTransform(
            [mouseX, mouseY],
            ([x, y]) =>
              `radial-gradient(${size}px circle at ${x}px ${y}px, ${fill}, transparent 80%)`,
          ),
        }}
      />
      {children}
    </div>
  )
}
