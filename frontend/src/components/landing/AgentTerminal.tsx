import { useState, useEffect, useRef } from 'react'
import { Play, Pause } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LogEntry {
  id: string
  time: string
  agent: 'RESEARCH' | 'PRICING' | 'RADAR' | 'SYSTEM'
  message: string
  severity: 'info' | 'success' | 'warn'
}

const INITIAL_LOGS: LogEntry[] = [
  {
    id: '1',
    time: '18:14:02.104',
    agent: 'SYSTEM',
    message: 'FastAPI worker pool initialized. 163 pytest assertions passed (0.84s).',
    severity: 'success',
  },
  {
    id: '2',
    time: '18:14:02.320',
    agent: 'RADAR',
    message: 'SP-API Buy Box poll completed: 48 active ASINs monitored. Win rate 94.6%.',
    severity: 'info',
  },
  {
    id: '3',
    time: '18:14:03.411',
    agent: 'PRICING',
    message: 'Competitor "TitanDirect" lowered ASIN B07X by $1.20 ($41.00 -> $39.80).',
    severity: 'warn',
  },
  {
    id: '4',
    time: '18:14:03.453',
    agent: 'PRICING',
    message: 'Counter-pricing dispatched: $39.79 (Unit margin: 23.8%, Floor: $31.50). Latency: 42ms.',
    severity: 'success',
  },
  {
    id: '5',
    time: '18:14:04.890',
    agent: 'RESEARCH',
    message: 'Gemini 2.0 Flash synthesized ASIN B0D1XD: Competitor review gap identified in silicone tip fatigue.',
    severity: 'info',
  },
  {
    id: '6',
    time: '18:14:05.112',
    agent: 'RESEARCH',
    message: 'Listing backend search terms optimized: +14 high-volume buyer intents indexed.',
    severity: 'success',
  },
]

export function AgentTerminal() {
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS)
  const [isPaused, setIsPaused] = useState(false)
  const [filter, setFilter] = useState<'ALL' | 'RESEARCH' | 'PRICING' | 'RADAR'>('ALL')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isPaused) return

    const dynamicMessages: Omit<LogEntry, 'id' | 'time'>[] = [
      {
        agent: 'PRICING',
        message: 'Elasticity model updated for Q4 peak: Recommended ceiling +$2.40.',
        severity: 'info',
      },
      {
        agent: 'RADAR',
        message: 'Suppression risk check passed for ASIN B09V3K. Buy Box stable.',
        severity: 'success',
      },
      {
        agent: 'RESEARCH',
        message: 'Market radar detected search surge: "insulated leak-proof tumbler" (+38% 7d volume).',
        severity: 'info',
      },
      {
        agent: 'SYSTEM',
        message: 'PostgreSQL pgvector query executed in 11ms: 12 similar product vectors matched.',
        severity: 'info',
      },
      {
        agent: 'PRICING',
        message: 'Automated Buy Box defense successful: 100% ownership maintained.',
        severity: 'success',
      },
      {
        agent: 'RESEARCH',
        message: 'Review sentiment audit complete for ASIN B08XYZ: 94.2% positive customer satisfaction.',
        severity: 'success',
      },
    ]

    const interval = setInterval(() => {
      const now = new Date()
      const timeStr = `${now.toTimeString().split(' ')[0]}.${String(
        now.getMilliseconds(),
      ).padStart(3, '0')}`
      const randomMsg = dynamicMessages[Math.floor(Math.random() * dynamicMessages.length)]

      setLogs((prev) => [
        ...prev.slice(-30),
        {
          id: Math.random().toString(),
          time: timeStr,
          ...randomMsg,
        },
      ])
    }, 2800)

    return () => clearInterval(interval)
  }, [isPaused])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  const filteredLogs = logs.filter((l) => (filter === 'ALL' ? true : l.agent === filter))

  return (
    <section id="telemetry" className="py-24 px-4 sm:px-6 max-w-6xl mx-auto w-full">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <span className="text-[11px] font-mono uppercase tracking-[0.25em] text-red-700 bg-red-50 px-3 py-1 rounded-full border border-red-200 font-semibold shadow-2xs">
          REAL-TIME TELEMETRY STREAM
        </span>
        <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 mt-4 mb-4">
          Live Agent Execution <span className="text-gradient-red">Console</span>
        </h2>
        <p className="text-slate-600 text-sm sm:text-base">
          Direct WebSocket feed showing sub-second agent inferences, market signals,
          and automated Buy Box repricing actions.
        </p>
      </div>

      {/* Terminal Window Frame */}
      <div className="rounded-2xl bg-slate-950 border border-slate-800 shadow-sm overflow-hidden font-mono text-xs text-left">
        {/* Terminal Title Bar */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="size-3 rounded-full bg-red-500 inline-block" />
            <span className="size-3 rounded-full bg-amber-500 inline-block" />
            <span className="size-3 rounded-full bg-emerald-500 inline-block" />
            <span className="ml-2 text-slate-400 text-[11px] font-bold">
              copilot-telemetry-cluster://agent-mesh-primary
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Filter buttons */}
            <div className="hidden sm:flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-[10px]">
              {(['ALL', 'RESEARCH', 'PRICING', 'RADAR'] as const).map((tag) => (
                <button
                  key={tag}
                  onClick={() => setFilter(tag)}
                  className={cn(
                    'px-2 py-0.5 rounded transition-colors cursor-pointer',
                    filter === tag
                      ? 'bg-red-600 text-white font-bold'
                      : 'text-slate-400 hover:text-white',
                  )}
                >
                  {tag}
                </button>
              ))}
            </div>

            {/* Pause button */}
            <button
              onClick={() => setIsPaused(!isPaused)}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10.5px] border border-slate-700 cursor-pointer"
            >
              {isPaused ? <Play className="size-3" /> : <Pause className="size-3" />}
              <span>{isPaused ? 'Resume' : 'Pause'}</span>
            </button>
          </div>
        </div>

        {/* Status Line */}
        <div className="flex items-center justify-between px-4 py-2 bg-slate-900/60 border-b border-slate-800 text-[10.5px] text-slate-400">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-red-400 font-bold">CONNECTED:</span>
            <span>4 LangGraph Workers Active · Mean Latency: 38ms · Pytest: 163/163 PASS</span>
          </div>
          <span className="hidden sm:inline text-slate-500">Buffer: 256KB/s</span>
        </div>

        {/* Scrollable Logs Viewport */}
        <div
          ref={scrollRef}
          className="h-80 overflow-y-auto p-4 space-y-2 bg-slate-950"
        >
          {filteredLogs.map((log) => (
            <div
              key={log.id}
              className="flex flex-col sm:flex-row sm:items-baseline gap-1.5 sm:gap-3 leading-relaxed hover:bg-slate-900/50 p-1 rounded transition-colors"
            >
              <span className="text-slate-500 shrink-0 text-[10px]">{log.time}</span>
              <span
                className={cn(
                  'px-1.5 py-0.2 rounded text-[10px] font-bold shrink-0',
                  log.agent === 'RESEARCH' && 'bg-purple-950/60 text-purple-400 border border-purple-800/50',
                  log.agent === 'PRICING' && 'bg-blue-950/60 text-blue-400 border border-blue-800/50',
                  log.agent === 'RADAR' && 'bg-amber-950/60 text-amber-400 border border-amber-800/50',
                  log.agent === 'SYSTEM' && 'bg-slate-800 text-slate-300 border border-slate-700',
                )}
              >
                [{log.agent}]
              </span>
              <span
                className={cn(
                  'text-xs break-all',
                  log.severity === 'success' && 'text-emerald-400',
                  log.severity === 'warn' && 'text-amber-300',
                  log.severity === 'info' && 'text-slate-300',
                )}
              >
                {log.message}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
