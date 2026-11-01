import { useRef, type ReactNode } from 'react'
import { motion, useMotionValue, useSpring, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils'

interface ShimmerButtonProps extends HTMLMotionProps<'button'> {
  children: ReactNode
  variant?: 'red' | 'emerald' | 'cyan' | 'obsidian' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  shimmerColor?: string
  shimmerDuration?: number
  glow?: boolean
  magnetic?: boolean
}

/**
 * Tactile button with spring physics, magnetic cursor pull, liquid crimson sheen, and enterprise styling.
 */
export function ShimmerButton({
  children,
  className,
  variant = 'red',
  size = 'md',
  shimmerColor = 'rgba(255, 255, 255, 0.25)',
  glow = false,
  magnetic = true,
  disabled,
  onMouseMove,
  onMouseLeave,
  ...props
}: ShimmerButtonProps) {
  const buttonRef = useRef<HTMLButtonElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const springConfig = { stiffness: 350, damping: 25 }
  const springX = useSpring(x, springConfig)
  const springY = useSpring(y, springConfig)

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (buttonRef.current && magnetic && !disabled) {
      const { left, top, width, height } = buttonRef.current.getBoundingClientRect()
      const centerX = left + width / 2
      const centerY = top + height / 2
      const distanceX = e.clientX - centerX
      const distanceY = e.clientY - centerY
      x.set(Math.max(-10, Math.min(10, distanceX * 0.22)))
      y.set(Math.max(-8, Math.min(8, distanceY * 0.22)))
    }
    onMouseMove?.(e)
  }

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    x.set(0)
    y.set(0)
    onMouseLeave?.(e)
  }

  const sizeClasses = {
    sm: 'px-3.5 py-1.5 text-xs rounded-lg gap-1.5',
    md: 'px-5 py-2.5 text-sm rounded-lg gap-2',
    lg: 'px-6 py-3 text-base rounded-xl gap-2.5 font-semibold',
  }

  const variantClasses = {
    red:
      'bg-red-600 hover:bg-red-700 active:bg-red-800 text-white shadow-sm hover:shadow-md border border-red-700/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.24)]',
    emerald:
      'bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-sm hover:shadow-md border border-emerald-700/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.24)]',
    cyan:
      'bg-slate-900 hover:bg-slate-800 text-white shadow-sm border border-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.15)]',
    obsidian:
      'bg-slate-950 text-white border border-slate-800 hover:bg-slate-900 shadow-sm shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]',
    outline:
      'bg-white text-slate-800 border border-slate-300 hover:bg-slate-50 hover:border-slate-400 shadow-2xs shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]',
  }

  return (
    <motion.button
      ref={buttonRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        x: magnetic ? springX : 0,
        y: magnetic ? springY : 0,
      }}
      whileHover={{ scale: disabled ? 1 : 1.015 }}
      whileTap={{ scale: disabled ? 1 : 0.985 }}
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      disabled={disabled}
      className={cn(
        'group relative inline-flex items-center justify-center font-medium tracking-tight overflow-hidden cursor-pointer select-none disabled:opacity-50 disabled:pointer-events-none transition-shadow duration-150',
        'before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent before:-translate-x-full hover:before:translate-x-full before:transition-transform before:duration-700 before:ease-out pointer-events-auto',
        sizeClasses[size],
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {/* Background radial glow */}
      {glow && (
        <span
          className="pointer-events-none absolute -inset-px rounded-[inherit] opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{
            background:
              variant === 'red' || variant === 'emerald'
                ? 'radial-gradient(120px circle, rgba(220, 38, 38, 0.25), transparent 70%)'
                : variant === 'cyan'
                ? 'radial-gradient(120px circle, rgba(37, 99, 235, 0.25), transparent 70%)'
                : 'radial-gradient(120px circle, rgba(0, 0, 0, 0.05), transparent 70%)',
          }}
        />
      )}

      {/* Sweeping Shimmer Highlight */}
      <span
        className="pointer-events-none absolute inset-0 -translate-x-full group-hover:animate-[shimmer_2s_infinite]"
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${shimmerColor} 50%, transparent 100%)`,
          transform: 'skewX(-20deg)',
        }}
      />

      {/* Button content */}
      <span className="relative z-10 flex items-center gap-2">{children}</span>
    </motion.button>
  )
}
