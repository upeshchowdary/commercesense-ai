import { Menu, PlayCircle, Search } from 'lucide-react'
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
import { NavLink, useNavigate } from 'react-router-dom'
import { NAV_ITEMS } from './Sidebar'
import { cn } from '@/lib/utils'
import { useProducts } from '@/hooks/useProducts'
import { useSignals } from '@/hooks/useSignals'

const QUICK_LINKS = [
  { label: 'Overview', to: '/overview' },
  { label: 'Products', to: '/products' },
  { label: 'Signals', to: '/signals' },
  { label: 'Research', to: '/research' },
  { label: 'AI Agents', to: '/agents' },
  { label: 'Decision Center', to: '/decisions' },
  { label: 'Evaluation', to: '/evaluation' },
  { label: 'Activity', to: '/activity' },
  { label: 'Settings', to: '/settings' },
]

export function Topbar({ title, actions }: { title: string; actions?: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [demoOpen, setDemoOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const navigate = useNavigate()
  // Global search reuses whatever React Query already has cached from
  // the currently mounted page — no dedicated /api/search endpoint,
  // per the plan's client-side-search scope simplification.
  const products = useProducts()
  const signals = useSignals()
  const productResults = useMemo(() => (products.data ?? []).slice(0, 8), [products.data])
  const signalResults = useMemo(() => (signals.data ?? []).slice(0, 8), [signals.data])

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
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileNavOpen(true)}
          className="flex size-8 items-center justify-center rounded-md border border-border text-muted-foreground md:hidden"
          aria-label="Open navigation"
        >
          <Menu className="size-4" />
        </button>
        <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      </div>
      <div className="flex items-center gap-2">
        {actions}
        <Button variant="outline" size="sm" onClick={() => setDemoOpen(true)}>
          <PlayCircle className="size-3.5" />
          Demo
        </Button>
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 rounded-md border border-border bg-panel px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <Search className="size-3.5" />
          Search
          <kbd className="ml-2 rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            ⌘K
          </kbd>
        </button>
      </div>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Jump to a page, product or signal…" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Navigate">
            {QUICK_LINKS.map((link) => (
              <CommandItem
                key={link.to}
                onSelect={() => {
                  navigate(link.to)
                  setOpen(false)
                }}
              >
                {link.label}
              </CommandItem>
            ))}
          </CommandGroup>
          {productResults.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Products">
                {productResults.map((p) => (
                  <CommandItem
                    key={p.product_id}
                    value={`product-${p.name}`}
                    onSelect={() => {
                      navigate(`/products/${p.product_id}`)
                      setOpen(false)
                    }}
                  >
                    {p.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
          {signalResults.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Signals">
                {signalResults.map((s) => (
                  <CommandItem
                    key={s.id}
                    value={`signal-${s.signal_type}-${s.product_name}`}
                    onSelect={() => {
                      navigate(`/signals/${s.id}`)
                      setOpen(false)
                    }}
                  >
                    {s.signal_type} · {s.product_name}
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </CommandDialog>
      <DemoMode open={demoOpen} onOpenChange={setDemoOpen} />
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-64 p-4">
          <nav className="mt-8 flex flex-col gap-0.5">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileNavOpen(false)}
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
        </SheetContent>
      </Sheet>
    </header>
  )
}
