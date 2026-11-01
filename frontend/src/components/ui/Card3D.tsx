import { useRef, useState, useCallback, type ReactNode } from 'react'
import { motion, useMotionValue, useSpring, useTransform, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils'

interface Card3DProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: ReactNode
  className?: string
  containerClassName?: string
  intensity?: number
  glareOpacity?: number
}

/**
 * GPU-accelerated 3D perspective tilt reacting to mouse position with specular glare.
 */
export function Card3D({
  children,
  className,
  containerClassName,
  intensity = 15,
  glareOpacity = 0.15,
  ...props
}: Card3DProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [isHovered, setIsHovered] = useState(false)

  const mouseX = useMotionValue(0.5)
  const mouseY = useMotionValue(0.5)

  // Spring physics for silky-smooth motion response
  const springX = useSpring(mouseX, { stiffness: 260, damping: 20 })
  const springY = useSpring(mouseY, { stiffness: 260, damping: 20 })

  const rotateX = useTransform(springY, [0, 1], [intensity, -intensity])
  const rotateY = useTransform(springX, [0, 1], [-intensity, intensity])

  const glareX = useTransform(springX, [0, 1], ['0%', '100%'])
  const glareY = useTransform(springY, [0, 1], ['0%', '100%'])

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!cardRef.current) return
      const rect = cardRef.current.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width
      const y = (e.clientY - rect.top) / rect.height
      mouseX.set(x)
      mouseY.set(y)
    },
    [mouseX, mouseY],
  )

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false)
    mouseX.set(0.5)
    mouseY.set(0.5)
  }, [mouseX, mouseY])

  return (
    <div
      style={{ perspective: 1000 }}
      className={cn('inline-block w-full', containerClassName)}
    >
      <motion.div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={handleMouseLeave}
        style={{
          rotateX,
          rotateY,
          transformStyle: 'preserve-3d',
        }}
        className={cn(
          'relative rounded-2xl transition-shadow duration-300 will-change-transform',
          className,
        )}
        {...props}
      >
        {children}

        {/* Specular Glare Layer */}
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-2xl transition-opacity duration-300"
          style={{
            opacity: isHovered ? glareOpacity : 0,
            background: useTransform(
              [glareX, glareY],
              ([gx, gy]) =>
                `radial-gradient(400px circle at ${gx} ${gy}, rgba(255, 255, 255, 0.4), transparent 80%)`,
            ),
          }}
        />
      </motion.div>
    </div>
  )
}

export function Card3DItem({
  children,
  className,
  translateZ = 30,
}: {
  children: ReactNode
  className?: string
  translateZ?: number
}) {
  return (
    <div
      style={{ transform: `translateZ(${translateZ}px)` }}
      className={cn('transition-transform duration-200', className)}
    >
      {children}
    </div>
  )
}
