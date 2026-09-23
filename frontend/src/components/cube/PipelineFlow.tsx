import { motion } from 'framer-motion'
import { ArrowRight, FileSearch, Gavel, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-react'

const STAGES = [
  { label: 'Research', icon: FileSearch },
  { label: 'Insight', icon: Sparkles },
  { label: 'Signal', icon: TriangleAlert },
  { label: 'Evidence', icon: ShieldCheck },
  { label: 'Decision', icon: Gavel },
]

export function PipelineFlow({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
        {STAGES.map((stage, i) => (
          <motion.div
            key={stage.label}
            className="flex items-center gap-2 sm:gap-3"
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-40px' }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
          >
            <div className="flex items-center gap-2 rounded-full border border-border bg-panel px-3.5 py-2 sm:px-4">
              <stage.icon className="size-3.5 text-primary" />
              <span className="text-xs font-medium text-foreground sm:text-sm">{stage.label}</span>
            </div>
            {i < STAGES.length - 1 && <ArrowRight className="size-3.5 text-muted-foreground" />}
          </motion.div>
        ))}
      </div>
    </div>
  )
}
