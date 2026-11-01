import {
  LayoutDashboard,
  Search,
  Boxes,
  Eye,
  Radio,
  Sparkles,
  DollarSign,
  Inbox,
  Zap,
  FileText,
  Link2,
  Settings as SettingsIcon,
  Activity,
  FlaskConical,
  ShieldCheck,
  Globe,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { getActions } from '@/lib/api'

export const NAV_GROUPS = [
  {
    title: 'WORKSPACE',
    items: [
      { to: '/overview', label: 'Overview', icon: LayoutDashboard },
      { to: '/research', label: 'Product Research', icon: Search },
      { to: '/products', label: 'Product Portfolio', icon: Boxes },
      { to: '/competitors', label: 'Competitor Watch', icon: Eye },
      { to: '/market-radar', label: 'Market Radar', icon: Radio },
      { to: '/opportunities', label: 'Product Opportunities', icon: Sparkles },
      { to: '/pricing-lab', label: 'Pricing Lab', icon: DollarSign },
    ],
  },
  {
    title: 'OPERATIONS',
    items: [
      { to: '/actions', label: 'Action Center', icon: Inbox, hasBadge: true },
      { to: '/automations', label: 'Automations', icon: Zap },
      { to: '/reports', label: 'Research Reports', icon: FileText },
    ],
  },
  {
    title: 'SETUP & DIAGNOSTICS',
    items: [
      { to: '/connections', label: 'Data Connections', icon: Link2 },
      { to: '/settings', label: 'Settings', icon: SettingsIcon },
      { to: '/diagnostics', label: 'Diagnostics', icon: FlaskConical },
      { to: '/activity', label: 'Audit & Activity', icon: Activity },
    ],
  },
]

// Flattened for mobile/command palette
export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items)

export function Sidebar() {
  const { data: queuedActions } = useQuery({
    queryKey: ['actions', 'QUEUED'],
    queryFn: () => getActions({ status: 'QUEUED' }),
    staleTime: 30_000,
  })

  const pendingCount = queuedActions?.length || 0

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white px-3.5 py-5 md:flex select-none shadow-xs">
      {/* Brand Header */}
      <NavLink to="/overview" className="mb-6 flex items-center gap-2.5 px-2 group">
        <div className="relative flex size-8 items-center justify-center rounded-xl bg-gradient-to-br from-red-600 to-red-700 text-white shadow-xs">
          <ShieldCheck className="size-4.5" />
          <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-red-400 animate-pulse" />
        </div>
        <div className="flex flex-col leading-tight">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-bold tracking-tight text-slate-900 group-hover:text-red-600 transition-colors">
              SELLER COPILOT
            </span>
            <span className="font-mono text-[9px] px-1 py-0.2 rounded bg-red-50 text-red-700 border border-red-200 font-bold">
              AI
            </span>
          </div>
          <span className="text-[10px] font-mono tracking-wider text-slate-500">
            SELLER CONTROL ROOM
          </span>
        </div>
      </NavLink>

      {/* Navigation Groups */}
      <nav className="flex flex-1 flex-col gap-5 overflow-y-auto pr-1">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="flex flex-col gap-1">
            <span className="px-2.5 text-[10px] font-mono font-bold tracking-wider text-slate-400">
              {group.title}
            </span>
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all duration-150',
                      isActive
                        ? 'bg-red-50 text-red-700 font-semibold border border-red-200/80 shadow-xs'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                    )
                  }
                >
                  <div className="flex items-center gap-2.5">
                    <item.icon className="size-4 shrink-0" />
                    <span>{item.label}</span>
                  </div>
                  {item.hasBadge && pendingCount > 0 && (
                    <span className="flex size-5 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white shadow-xs">
                      {pendingCount > 9 ? '9+' : pendingCount}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Store / Marketplace Context Bar */}
      <div className="mt-auto pt-3 border-t border-slate-200">
        <div className="flex items-center justify-between rounded-xl bg-slate-50 border border-slate-200 p-2.5 text-xs">
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <Globe className="size-3 text-red-600" />
              <span className="font-semibold text-slate-900 text-[11px]">Amazon India</span>
            </div>
            <span className="font-mono text-[10px] text-slate-500">IN (₹) · A21TJRUUN4KGV</span>
          </div>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-emerald-500 animate-pulse" title="SP-API Synchronized" />
          </span>
        </div>
      </div>
    </aside>
  )
}
