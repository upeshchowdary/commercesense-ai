import {
  Activity,
  Bot,
  Boxes,
  Gavel,
  LayoutDashboard,
  Search,
  Settings,
  TriangleAlert,
  Waypoints,
  FlaskConical,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

export const NAV_ITEMS = [
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/products', label: 'Products', icon: Boxes },
  { to: '/signals', label: 'Signals', icon: TriangleAlert },
  { to: '/research', label: 'Research', icon: Search },
  { to: '/agents', label: 'AI Agents', icon: Bot },
  { to: '/decisions', label: 'Decision Center', icon: Gavel },
  { to: '/evaluation', label: 'Evaluation', icon: FlaskConical },
  { to: '/activity', label: 'Activity', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-panel/60 px-3 py-5 md:flex">
      <NavLink to="/overview" className="mb-6 flex items-center gap-2 px-2">
        <div className="flex size-7 items-center justify-center rounded-md border border-primary/40 bg-primary/10">
          <Waypoints className="size-4 text-primary" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold text-foreground">Sydon-1</span>
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Commerce Intel</span>
        </div>
      </NavLink>

      <nav className="flex flex-1 flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                isActive && 'bg-muted text-foreground',
              )
            }
          >
            <item.icon className="size-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="rounded-lg border border-border bg-card px-3 py-2.5 text-[11px] text-muted-foreground">
        CUBE Buildathon practice build — Sydon AI / CodeQuesters
      </div>
    </aside>
  )
}
