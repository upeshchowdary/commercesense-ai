import { Menu, PlayCircle, Search, Inbox, ShieldCheck, Globe } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { DemoMode } from '@/components/demo/DemoMode'
import { ThemeToggle } from '@/components/shared/ThemeToggle'
import { NavLink, useNavigate } from 'react-router-dom'
import { NAV_GROUPS } from './Sidebar'
import { cn } from '@/lib/utils'
import { useProducts } from '@/hooks/useProducts'
import { useQuery } from '@tanstack/react-query'
import { getActions } from '@/lib/api'

export function Topbar({ title, actions }: { title: string; actions?: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [demoOpen, setDemoOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const navigate = useNavigate()

  const products = useProducts()
  const { data: queuedActions } = useQuery({
    queryKey: ['actions', 'QUEUED'],
    queryFn: () => getActions({ status: 'QUEUED' }),
    staleTime: 30_000,
  })

  const pendingCount = queuedActions?.length || 0
  const productResults = useMemo(() => (products.data ?? []).slice(0, 10), [products.data])

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen((v) => !v)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <header className="flex h-15 shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white/90 backdrop-blur-md px-4 sm:px-6 z-20">
      {/* Title & Mobile Toggle */}
      <div className="flex min-w-0 items-center gap-3">
        <button
          onClick={() => setMobileNavOpen(true)}
          className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900 md:hidden cursor-pointer"
          aria-label="Open navigation"
        >
          <Menu className="size-4" />
        </button>
        <div className="flex items-center gap-2.5">
          <h1 className="truncate text-base font-bold text-slate-900 tracking-tight">
            {title}
          </h1>
          <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10.5px] font-mono font-medium bg-red-50 text-red-700 border border-red-200">
            <span className="size-1.5 rounded-full bg-red-600 animate-pulse" />
            <Globe className="size-3" /> Amazon.in (₹)
          </span>
        </div>
      </div>

      {/* Topbar Actions */}
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        {actions}

        {/* Global Search Button */}
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600 transition-colors hover:text-slate-900 hover:border-slate-300 sm:px-3.5 cursor-pointer shadow-xs"
        >
          <Search className="size-3.5" />
          <span className="hidden sm:inline">Search portfolio & alerts…</span>
          <kbd className="ml-2 hidden rounded border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-[10px] text-slate-500 sm:inline shadow-2xs">
            ⌘K
          </kbd>
        </button>

        {/* Action Center Shortcut with real badge */}
        <button
          onClick={() => navigate('/actions')}
          className="relative flex size-8 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900 hover:border-slate-300 transition-colors cursor-pointer shadow-xs"
          title="Open Action Center"
        >
          <Inbox className="size-4" />
          {pendingCount > 0 && (
            <span className="absolute -top-1 -right-1 flex size-4 items-center justify-center rounded-full bg-red-600 text-[9px] font-bold text-white shadow-xs">
              {pendingCount > 9 ? '9+' : pendingCount}
            </span>
          )}
        </button>

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* Demo Mode Trigger */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setDemoOpen(true)}
          className="border-slate-200 bg-slate-50 text-slate-700 hover:bg-red-50 hover:text-red-700 hover:border-red-200 rounded-xl"
        >
          <PlayCircle className="size-3.5 text-red-600" />
          <span className="hidden sm:inline">Demo Mode</span>
        </Button>
      </div>

      {/* Mobile Navigation Drawer */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 p-0 bg-white border-r border-slate-200 text-slate-700">
          <div className="flex flex-col h-full p-4">
            <div className="flex items-center gap-2 mb-6">
              <div className="flex size-7 items-center justify-center rounded-lg bg-red-50 text-red-600 border border-red-200">
                <ShieldCheck className="size-4" />
              </div>
              <span className="font-bold text-sm text-slate-900">SELLER COPILOT // CONTROL ROOM</span>
            </div>
            <nav className="flex flex-col gap-4 overflow-y-auto">
              {NAV_GROUPS.map((group) => (
                <div key={group.title} className="flex flex-col gap-1">
                  <span className="text-[10px] font-mono font-bold text-slate-400 px-2">{group.title}</span>
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileNavOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center justify-between rounded-lg px-2.5 py-2 text-sm font-medium transition-colors',
                          isActive
                            ? 'bg-red-50 text-red-700 border border-red-200/80 font-semibold'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                        )
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <item.icon className="size-4" />
                        <span>{item.label}</span>
                      </div>
                      {item.hasBadge && pendingCount > 0 && (
                        <span className="flex size-5 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white shadow-xs">
                          {pendingCount}
                        </span>
                      )}
                    </NavLink>
                  ))}
                </div>
              ))}
            </nav>
          </div>
        </SheetContent>
      </Sheet>

      {/* Command Palette (Ctrl+K) */}
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Search pages, products, or signals…" />
        <CommandList className="bg-white text-slate-800 border-slate-200">
          <CommandEmpty>No matching results found.</CommandEmpty>

          <CommandGroup heading="Navigation">
            {NAV_GROUPS.flatMap((g) => g.items).map((link) => (
              <CommandItem
                key={link.to}
                onSelect={() => {
                  navigate(link.to)
                  setOpen(false)
                }}
              >
                <link.icon className="size-4 mr-2 text-slate-500" />
                <span>{link.label}</span>
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator className="bg-slate-200" />

          <CommandGroup heading="Product Portfolio">
            {productResults.map((p) => (
              <CommandItem
                key={p.product_id}
                onSelect={() => {
                  navigate(`/products/${encodeURIComponent(p.product_id)}`)
                  setOpen(false)
                }}
              >
                <span className="font-medium mr-2 text-slate-900">{p.name}</span>
                <span className="text-xs text-slate-500">({p.category} · ${p.base_price.toFixed(2)})</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>

      <DemoMode open={demoOpen} onOpenChange={setDemoOpen} />
    </header>
  )
}
