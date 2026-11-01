import { useEffect, useRef } from 'react'

/*
  Dependency-free 3D "product universe": a Fibonacci-sphere point cloud
  projected with perspective onto a 2D canvas. It rotates slowly and
  leans toward the pointer. Amber points are "flagged" products that
  pulse. It is purely decorative, so it's aria-hidden and honors
  prefers-reduced-motion.
*/
export function HeroGlobe({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const N = 900
    const pts = Array.from({ length: N }, (_, i) => {
      const y = 1 - (i / (N - 1)) * 2
      const r = Math.sqrt(1 - y * y)
      const t = i * Math.PI * (3 - Math.sqrt(5))
      return { x: Math.cos(t) * r, y, z: Math.sin(t) * r, hot: i % 37 === 0, phase: (i * 0.618) % 1 }
    })

    let w = 0
    let h = 0
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = canvas.clientWidth
      h = canvas.clientHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    let mx = 0
    let my = 0
    let tx = 0
    let ty = 0
    const onMove = (e: PointerEvent) => {
      tx = e.clientX / window.innerWidth - 0.5
      ty = e.clientY / window.innerHeight - 0.5
    }
    window.addEventListener('pointermove', onMove)

    let blue = '#4fc3f7'
    let amber = '#e8a33d'
    const readColors = () => {
      const css = getComputedStyle(document.documentElement)
      blue = css.getPropertyValue('--blue').trim() || blue
      amber = css.getPropertyValue('--amber').trim() || amber
    }
    readColors()
    const mo = new MutationObserver(readColors)
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })

    let raf = 0
    let rot = 0
    let time = 0
    const draw = () => {
      mx += (tx - mx) * 0.05
      my += (ty - my) * 0.05
      if (!reduce) {
        rot += 0.0022
        time += 0.016
      }
      ctx.clearRect(0, 0, w, h)
      const R = Math.min(w, h) * 0.36
      const cx = w / 2
      const cy = h / 2
      const ay = rot + mx * 0.9
      const ax = 0.35 + my * 0.7
      const cA = Math.cos(ay)
      const sA = Math.sin(ay)
      const cB = Math.cos(ax)
      const sB = Math.sin(ax)

      // Orbit ring, tilted with the globe
      ctx.globalAlpha = 0.25
      ctx.strokeStyle = blue
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.ellipse(cx, cy, R * 1.45, R * 0.42, -0.25 + mx * 0.3, 0, Math.PI * 2)
      ctx.stroke()

      for (const p of pts) {
        const x1 = p.x * cA - p.z * sA
        const z1 = p.x * sA + p.z * cA
        const y2 = p.y * cB - z1 * sB
        const z2 = p.y * sB + z1 * cB
        const persp = 1.3 / (2 - z2)
        const sx = cx + x1 * R * persp * 1.5
        const sy = cy + y2 * R * persp * 1.5
        const depth = (z2 + 1) / 2
        ctx.globalAlpha = 0.08 + depth * 0.8
        ctx.fillStyle = p.hot ? amber : blue
        ctx.beginPath()
        ctx.arc(sx, sy, (p.hot ? 2.6 : 1.1) * (0.45 + depth), 0, Math.PI * 2)
        ctx.fill()
        if (p.hot && depth > 0.55) {
          const k = (time * 0.6 + p.phase) % 1
          ctx.globalAlpha = (1 - k) * 0.7 * depth
          ctx.strokeStyle = amber
          ctx.beginPath()
          ctx.arc(sx, sy, 3 + k * 16, 0, Math.PI * 2)
          ctx.stroke()
        }
      }
      ctx.globalAlpha = 1
      raf = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      mo.disconnect()
      window.removeEventListener('pointermove', onMove)
    }
  }, [])

  return <canvas ref={ref} aria-hidden className={className} />
}
