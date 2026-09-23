import { ArrowRight, PlayCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { CubeHero } from '@/components/cube/CubeHero'
import { PipelineFlow } from '@/components/cube/PipelineFlow'
import { DemoMode } from '@/components/demo/DemoMode'

export default function Landing() {
  const [demoOpen, setDemoOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-10 px-6 py-16">
      <CubeHero />
      <div className="flex max-w-2xl flex-col items-center gap-4 text-center">
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
          Sydon-1 · CUBE Buildathon Practice Build
        </span>
        <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
          AI Agents for{' '}
          <span className="text-gradient-blue">Continuous Commerce Intelligence</span>
        </h1>
        <p className="max-w-xl text-balance text-muted-foreground">
          Research markets, detect important signals, explain the evidence, and surface decisions
          that matter.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button size="lg" asChild>
          <Link to="/overview">
            Explore Intelligence
            <ArrowRight className="size-4" />
          </Link>
        </Button>
        <Button size="lg" variant="outline" onClick={() => setDemoOpen(true)}>
          <PlayCircle className="size-4" />
          Run Demo
        </Button>
      </div>
      <PipelineFlow className="mt-6" />
      <DemoMode open={demoOpen} onOpenChange={setDemoOpen} />
    </div>
  )
}
