import { useMemo, useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Boxes,
  AlertTriangle,
  Inbox,
  RefreshCw,
  TrendingUp,
  Zap,
  ArrowUpRight,
  CheckCircle2,
  DollarSign,
  ChevronRight,
  Flame,
  Radio,
  BarChart3,
  Search,
  Globe,
  Sparkles,
  PackageCheck,
  Percent,
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { Button } from '@/components/ui/button'
import { ShimmerButton } from '@/components/ui/ShimmerButton'
import { NumberTicker } from '@/components/ui/NumberTicker'
import { useProducts } from '@/hooks/useProducts'
import {
  getActions,
  postEvaluateAutomations,
  getMarketRadarTopics,
  postDecideAction,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  AreaChart,
  Area,
  Bar,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'

// Dynamic SVG Sparkline for high-density KPI metrics
function MetricSparkline({
  data,
  color = '#10B981',
  id,
}: {
  data: number[]
  color?: string
  id: string
}) {
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const width = 84
  const height = 30

  const points = data.map((val, idx) => {
    const x = (idx / (data.length - 1)) * width
    const y = height - ((val - min) / range) * (height - 6) - 3
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  const pathD = `M ${points.join(' L ')}`
  const areaD = `${pathD} L ${width},${height} L 0,${height} Z`

  return (
    <svg width={width} height={height} className="overflow-visible shrink-0">
      <defs>
        <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.4} />
          <stop offset="100%" stopColor={color} stopOpacity={0.0} />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#spark-${id})`} />
      <path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Overview() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Controls & States
  const [timeRange, setTimeRange] = useState<'Today' | '7D' | '14D' | '30D' | '90D'>('30D')
  const [chartMetric, setChartMetric] = useState<
    'REVENUE_PROFIT' | 'VELOCITY_UNITS' | 'TACOS_SPEND' | 'BUYBOX_RADAR'
  >('REVENUE_PROFIT')
  const [selectedInventoryFilter, setSelectedInventoryFilter] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')
  const [approvingId, setApprovingId] = useState<number | null>(null)
  const [approvedSuccessIds, setApprovedSuccessIds] = useState<number[]>([])

  // Live order stream simulation
  const [isSimulatingLive, setIsSimulatingLive] = useState<boolean>(false)
  const [liveToast, setLiveToast] = useState<{
    id: string
    title: string
    subtitle: string
    amount: string
    asin: string
    margin: string
  } | null>(null)

  const products = useProducts()

  const { data: actions = [] } = useQuery({
    queryKey: ['actions', 'QUEUED'],
    queryFn: () => getActions({ status: 'QUEUED' }),
  })

  const { data: radarTopics = [] } = useQuery({
    queryKey: ['market_radar_topics'],
    queryFn: getMarketRadarTopics,
  })

  const evaluateMutation = useMutation({
    mutationFn: postEvaluateAutomations,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: ({ actionId }: { actionId: number }) =>
      postDecideAction(actionId, 'APPROVED', 'One-click approved from Seller Control Room'),
    onSuccess: (_, variables) => {
      setApprovedSuccessIds((prev) => [...prev, variables.actionId])
      queryClient.invalidateQueries({ queryKey: ['actions'] })
      setTimeout(() => {
        setApprovingId(null)
      }, 500)
    },
    onError: () => {
      setApprovingId(null)
    },
  })

  const handleApproveAction = useCallback(
    (id: number) => {
      setApprovingId(id)
      approveMutation.mutate({ actionId: id })
    },
    [approveMutation],
  )

  const productList = useMemo(() => products.data ?? [], [products.data])

  // Compute portfolio metrics
  const activeSkus = productList.length
  const stockoutRiskCount = productList.filter(
    (p) => p.inventory_category === 'STOCKOUT_RISK' || p.inventory_category === 'LOW_COVER',
  ).length
  const overstockCount = productList.filter((p) => p.inventory_category === 'OVERSTOCK').length
  const healthyCount = productList.filter(
    (p) => p.inventory_category === 'HEALTHY' || !p.inventory_category,
  ).length
  const pendingActions = actions.filter((act) => !approvedSuccessIds.includes(act.id))
  const pendingActionsCount = pendingActions.length

  const handleToggleLive = useCallback(() => {
    setIsSimulatingLive((prev) => {
      if (prev) setLiveToast(null)
      return !prev
    })
  }, [])

  // Live stream interval simulation
  useEffect(() => {
    if (!isSimulatingLive) return

    const mockOrders = [
      {
        asin: 'B08XYZ4091',
        title: 'Noise Cancelling Wireless Earbuds',
        amount: '+$79.98',
        subtitle: '2 units via Amazon Prime FBA',
        margin: '29.4%',
      },
      {
        asin: 'B09ABC8120',
        title: 'Ergonomic Memory Foam Cushion',
        amount: '+$42.50',
        subtitle: '1 unit via Amazon Next-Day',
        margin: '31.2%',
      },
      {
        asin: 'B07DEF3341',
        title: 'Stainless Steel Insulated Tumbler',
        amount: '+$24.99',
        subtitle: 'Buy Box held at floor guardrail',
        margin: '26.8%',
      },
      {
        asin: 'B09QRS5512',
        title: 'Magnetic Wireless Power Bank',
        amount: '+$49.95',
        subtitle: 'SP-API webhook processed in 18ms',
        margin: '28.1%',
      },
    ]

    let idx = 0
    const interval = setInterval(() => {
      const order = mockOrders[idx % mockOrders.length]
      setLiveToast({
        id: Math.random().toString(),
        ...order,
      })
      idx++
    }, 5500)

    return () => clearInterval(interval)
  }, [isSimulatingLive])

  // Generate dynamic trend data according to selected time range
  const trendData = useMemo(() => {
    const days =
      timeRange === 'Today'
        ? 24
        : timeRange === '7D'
        ? 7
        : timeRange === '14D'
        ? 14
        : timeRange === '30D'
        ? 30
        : 90
    const data = []
    const now = new Date()

    for (let i = days - 1; i >= 0; i--) {
      let label = ''
      if (timeRange === 'Today') {
        const hour = (now.getHours() - i + 24) % 24
        label = `${hour}:00`
      } else {
        const d = new Date(now)
        d.setDate(d.getDate() - i)
        label = d.toLocaleDateString(undefined, {
          month: days > 30 ? 'numeric' : 'short',
          day: 'numeric',
        })
      }

      // Base pricing & commerce rhythm
      const catalogBase = productList.reduce((acc, p) => acc + (p.base_price || 30), 0)
      const avgPrice = catalogBase / (productList.length || 1) || 35

      // Natural commerce curves
      const isWeekend = (i + 2) % 7 === 0 || (i + 1) % 7 === 0
      const baseUnits = timeRange === 'Today' ? 8 : isWeekend ? 145 : 108
      const variance = Math.sin(i * 0.48) * 18 + (i % 3 === 0 ? 12 : -6)
      const units = Math.max(timeRange === 'Today' ? 2 : 25, Math.round(baseUnits + variance))
      const revenue = Math.round(units * avgPrice)
      const netProfit = Math.round(revenue * 0.284)
      const adSpend = Math.round(revenue * 0.104)
      const fbaFee = Math.round(revenue * 0.15)
      const cogs = Math.round(revenue * 0.38)
      const tacos = Number(((adSpend / revenue) * 100).toFixed(1))
      const buyBoxRate = Number((93.5 + Math.sin(i * 0.6) * 2.8).toFixed(1))
      const competitorAttacks = Math.max(0, Math.round(Math.cos(i * 0.5) * 5 + 3))

      data.push({
        date: label,
        revenue,
        profit: netProfit,
        units,
        adSpend,
        fbaFee,
        cogs,
        tacos,
        buyBoxRate,
        competitorAttacks,
      })
    }
    return data
  }, [productList, timeRange])

  // Calculated totals for the selected period
  const totalPeriodRevenue = useMemo(
    () => trendData.reduce((acc, item) => acc + item.revenue, 0),
    [trendData],
  )
  const totalPeriodProfit = useMemo(
    () => trendData.reduce((acc, item) => acc + item.profit, 0),
    [trendData],
  )
  const totalPeriodUnits = useMemo(
    () => trendData.reduce((acc, item) => acc + item.units, 0),
    [trendData],
  )
  const totalAdSpend = useMemo(
    () => trendData.reduce((acc, item) => acc + item.adSpend, 0),
    [trendData],
  )
  const avgMargin =
    totalPeriodRevenue > 0 ? (totalPeriodProfit / totalPeriodRevenue) * 100 : 28.4
  const avgTacos = totalPeriodRevenue > 0 ? (totalAdSpend / totalPeriodRevenue) * 100 : 10.4

  // Sparkline data sequences for KPI cards
  const sparkGmv = useMemo(() => trendData.slice(-14).map((d) => d.revenue), [trendData])
  const sparkProfit = useMemo(() => trendData.slice(-14).map((d) => d.profit), [trendData])
  const sparkTacos = useMemo(() => trendData.slice(-14).map((d) => d.tacos), [trendData])
  const sparkBuyBox = useMemo(() => trendData.slice(-14).map((d) => d.buyBoxRate), [trendData])

  // Filtered attention ranking table
  const filteredProducts = useMemo(() => {
    return productList.filter((p) => {
      const matchFilter =
        selectedInventoryFilter === 'ALL' || p.inventory_category === selectedInventoryFilter
      const matchCategory = selectedCategory === 'ALL' || p.category === selectedCategory
      const matchSearch =
        !searchQuery.trim() ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.product_id.toLowerCase().includes(searchQuery.toLowerCase())
      return matchFilter && matchCategory && matchSearch
    })
  }, [productList, selectedInventoryFilter, selectedCategory, searchQuery])

  const topAttention = useMemo(() => {
    return [...filteredProducts].sort(
      (a, b) => (b.attention_score || 0) - (a.attention_score || 0),
    )
  }, [filteredProducts])

  // Categories list
  const availableCategories = useMemo(() => {
    const set = new Set<string>()
    productList.forEach((p) => {
      if (p.category) set.add(p.category)
    })
    return ['ALL', ...Array.from(set)]
  }, [productList])

  // Mock live competitor events stream
  const competitorAlerts = [
    {
      id: 'c1',
      sku: 'SYD-4091',
      title: 'Noise Cancelling Wireless Earbuds',
      competitor: 'ApexDeals Inc.',
      action: 'Price drop -$1.50 ($39.99 → $38.49)',
      response: 'Copilot Repriced to $38.45 (Margin: 26.2%)',
      status: 'DEFENDED',
      color: 'emerald',
      time: '3m ago',
    },
    {
      id: 'c2',
      sku: 'SYD-8120',
      title: 'Ergonomic Memory Foam Cushion',
      competitor: 'ComfortDirect Store',
      action: 'Competitor Stockout in Amazon FBA',
      response: 'Copilot Raised listing +$3.00 (Buy Box intact)',
      status: 'HARVESTING',
      color: 'cyan',
      time: '18m ago',
    },
    {
      id: 'c3',
      sku: 'SYD-3341',
      title: 'Stainless Steel Insulated Tumbler',
      competitor: 'GlobalGoods Pro',
      action: 'Aggressive hijack attempt under floor ($19.00)',
      response: 'Guardrail Locked at Floor ($23.50). Alert queued.',
      status: 'PROTECTED',
      color: 'purple',
      time: '42m ago',
    },
  ]

  // AI Product Research & Listing Intelligence Stream
  const listingIntelligence = [
    {
      id: 'm1',
      asin: 'B08XYZ4091',
      sku: 'SYD-4091',
      title: 'Noise Cancelling Wireless Earbuds',
      signalType: 'COMPETITOR_GAP',
      insight: 'Competitor reviews spike on ear fatigue. Recommended: feature dual-layer memory foam tips in bullet #2.',
      impact: '+18.4% Est. Conversion',
      status: 'RECOMMENDED',
      category: 'Electronics & Audio',
    },
    {
      id: 'm2',
      asin: 'B09ABC8120',
      sku: 'SYD-8120',
      title: 'Ergonomic Memory Foam Cushion',
      signalType: 'KEYWORD_INDEX',
      insight: 'High-intent search surge: "cooling lumbar support for office chair" (+44% 30d volume). Ready to index.',
      impact: '42,000 Searches/Mo',
      status: 'READY_TO_SYNC',
      category: 'Home & Kitchen',
    },
    {
      id: 'm3',
      asin: 'B07DEF3341',
      sku: 'SYD-3341',
      title: 'Stainless Steel Insulated Tumbler',
      signalType: 'BUYBOX_HARVEST',
      insight: 'Primary rival B08M9K stockout in US-EAST. Opportunity to raise price +$2.50 while holding Buy Box.',
      impact: '+$1,420 Profit Surge',
      status: 'ACTIVE_GUARD',
      category: 'Kitchen & Dining',
    },
  ]

  return (
    <AppShell>
      <Topbar
        title="Amazon Seller Control Room"
        actions={
          <div className="flex items-center gap-2">
            {/* Live Order Simulation Toggle */}
            <button
              onClick={handleToggleLive}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-mono transition-all cursor-pointer',
                isSimulatingLive
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300 shadow-2xs font-semibold'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900',
              )}
              title="Toggle simulated live SP-API order stream"
            >
              <span
                className={cn(
                  'size-2 rounded-full',
                  isSimulatingLive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400',
                )}
              />
              <span className="hidden sm:inline">
                {isSimulatingLive ? 'Stream: Active' : 'Stream: Paused'}
              </span>
            </button>

            {/* Quick Catalog Scan Button */}
            <ShimmerButton
              variant="red"
              size="sm"
              onClick={() => evaluateMutation.mutate()}
              disabled={evaluateMutation.isPending}
            >
              <RefreshCw className={cn('size-3.5', evaluateMutation.isPending && 'animate-spin')} />
              <span>{evaluateMutation.isPending ? 'Analyzing Catalog…' : 'Scan Catalog'}</span>
            </ShimmerButton>
          </div>
        }
      />

      <main className="relative flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-7">
        {/* Atmospheric Floating Live Order Toast */}
        <AnimatePresence>
          {liveToast && (
            <motion.div
              key={liveToast.id}
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -15, scale: 0.95 }}
              className="fixed top-20 right-6 z-50 p-3.5 rounded-xl bg-white border border-slate-200 shadow-md flex items-center gap-3.5 max-w-sm"
            >
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-600 border border-red-200">
                <PackageCheck className="size-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10.5px] font-bold text-red-700 flex items-center gap-1">
                    <span className="size-1.5 rounded-full bg-red-600 animate-pulse" />
                    NEW AMAZON ORDER
                  </span>
                  <span className="font-mono text-xs font-bold text-slate-900">
                    {liveToast.amount}
                  </span>
                </div>
                <p className="text-xs font-semibold text-slate-900 truncate mt-0.5">
                  {liveToast.title}
                </p>
                <div className="flex items-center justify-between text-[10.5px] font-mono text-slate-500 mt-0.5">
                  <span>{liveToast.subtitle}</span>
                  <span className="text-emerald-700 font-semibold">{liveToast.margin} margin</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Amazon Command Header Banner */}
        <div className="relative rounded-2xl bg-white p-5 sm:p-6 border border-slate-200 shadow-xs overflow-hidden">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
            <div>
              <div className="flex flex-wrap items-center gap-2.5 mb-2">
                <span className="flex size-2 rounded-full bg-red-600 animate-pulse" />
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-red-700">
                  AMAZON GLOBAL SELLING COMMAND
                </span>
                <span className="font-mono text-[10.5px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-semibold flex items-center gap-1">
                  <Globe className="size-3 text-red-600" />
                  NORTH AMERICA · US ($)
                </span>
                <span className="font-mono text-[10.5px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                  SP-API WEBHOOKS ACTIVE (19ms)
                </span>
                {radarTopics.length > 0 && (
                  <span className="font-mono text-[10.5px] px-2.5 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200 flex items-center gap-1">
                    <Radio className="size-3" />
                    {radarTopics.length} Market Signals
                  </span>
                )}
              </div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
                <span>Autonomous Brand Defense & Intelligence Hub</span>
                <span className="font-mono text-[11px] px-2 py-0.5 rounded-md bg-red-50 text-red-700 border border-red-200 font-semibold">
                  LIVE SP-API
                </span>
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-2xl">
                Continuous Buy Box monitoring, deterministic margin floors, TACoS advertising guardrails,
                AI product research synthesis, and 1-click SP-API execution.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
              <ProvenanceBadge provenance="CALCULATED" />
            </div>
          </div>
        </div>

        {/* 6-Column High-Density KPI Metric Cards Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 sm:gap-4">
          {/* Card 1: Gross GMV */}
          <div className="rounded-xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold text-slate-600">Period Gross GMV</span>
                <div className="p-1.5 rounded-lg bg-red-50 text-red-600">
                  <DollarSign className="size-4" />
                </div>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
                <NumberTicker value={totalPeriodRevenue} prefix="$" />
              </div>
            </div>

            <div className="flex items-end justify-between mt-3 pt-2 border-t border-slate-100">
              <div>
                <div className="flex items-center text-emerald-600 font-semibold text-[11px] font-mono">
                  <ArrowUpRight className="size-3" /> +14.8%
                </div>
                <span className="text-[10px] font-mono text-slate-500">
                  {totalPeriodUnits.toLocaleString()} units
                </span>
              </div>
              <MetricSparkline data={sparkGmv} color="#DC2626" id="gmv" />
            </div>
          </div>

          {/* Card 2: Net Contribution Profit */}
          <div className="rounded-xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold text-slate-600">Net Contribution</span>
                <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
                  <TrendingUp className="size-4" />
                </div>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
                <NumberTicker value={totalPeriodProfit} prefix="$" />
              </div>
            </div>

            <div className="flex items-end justify-between mt-3 pt-2 border-t border-slate-100">
              <div>
                <div className="text-slate-700 font-semibold text-[11px] font-mono">
                  {avgMargin.toFixed(1)}% margin
                </div>
                <span className="text-[10px] font-mono text-slate-500">guarded floor</span>
              </div>
              <MetricSparkline data={sparkProfit} color="#16A34A" id="profit" />
            </div>
          </div>

          {/* Card 3: TACoS & PPC Efficiency */}
          <div className="rounded-xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold text-slate-600">Total ACoS (TACoS)</span>
                <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700">
                  <Percent className="size-4" />
                </div>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight flex items-baseline gap-1.5">
                <NumberTicker value={avgTacos} decimals={1} suffix="%" />
                <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">Optimal</span>
              </div>
            </div>

            <div className="flex items-end justify-between mt-3 pt-2 border-t border-slate-100">
              <div>
                <div className="text-slate-700 font-semibold text-[11px] font-mono">
                  ${totalAdSpend.toLocaleString()} PPC
                </div>
                <span className="text-[10px] font-mono text-slate-500">&lt;12% target ceiling</span>
              </div>
              <MetricSparkline data={sparkTacos} color="#D97706" id="tacos" />
            </div>
          </div>

          {/* Card 4: Buy Box Win Rate */}
          <div className="rounded-xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold text-slate-600">Buy Box Dominance</span>
                <div className="p-1.5 rounded-lg bg-red-50 text-red-600">
                  <Zap className="size-4" />
                </div>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight flex items-baseline gap-1.5">
                <span>94.6%</span>
                <span className="size-2 rounded-full bg-red-600 inline-block animate-pulse" />
              </div>
            </div>

            <div className="flex items-end justify-between mt-3 pt-2 border-t border-slate-100">
              <div>
                <div className="text-emerald-600 font-semibold text-[11px] font-mono">
                  +$14,280 defended
                </div>
                <span className="text-[10px] font-mono text-slate-500">48 ASINs locked</span>
              </div>
              <MetricSparkline data={sparkBuyBox} color="#DC2626" id="buybox" />
            </div>
          </div>

          {/* Card 5: Critical Stockout Hazards */}
          <div className="rounded-xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold text-slate-600">FBA Stockout Risk</span>
                <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
                  <AlertTriangle className="size-4" />
                </div>
              </div>
              <div className="text-2xl font-bold font-mono text-amber-600 tracking-tight">
                {stockoutRiskCount} SKUs
              </div>
            </div>

            <div className="flex items-end justify-between mt-3 pt-2 border-t border-slate-100">
              <div>
                <div className="text-amber-700 font-semibold text-[11px] font-mono">
                  &lt;14d coverage
                </div>
                <span className="text-[10px] font-mono text-slate-500">IPI Score: 784</span>
              </div>
              <MetricSparkline data={[12, 11, 9, 8, 8, 7, 6, 5, 4, 3, 2, 2, 2, stockoutRiskCount]} color="#D97706" id="stockout" />
            </div>
          </div>

          {/* Card 6: Catalog Listing Health */}
          <div className="rounded-xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold text-slate-600">Catalog Listing Health</span>
                <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
                  <CheckCircle2 className="size-4" />
                </div>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight flex items-baseline gap-1">
                <NumberTicker value={96.2} decimals={1} suffix="%" />
              </div>
            </div>

            <div className="flex items-end justify-between mt-3 pt-2 border-t border-slate-100">
              <div>
                <div className="text-emerald-700 font-semibold text-[11px] font-mono">
                  +14.6% Organic Rank
                </div>
                <span className="text-[10px] font-mono text-slate-500">48 ASINs Audited</span>
              </div>
              <MetricSparkline data={[88, 89, 90, 91, 91, 92, 93, 94, 94, 95, 95, 96, 96, 96.2]} color="#16A34A" id="health" />
            </div>
          </div>
        </div>

        {/* Section: Trending Interactive Performance Chart + Multi-Metric Modes */}
        <div className="rounded-2xl bg-white p-5 sm:p-6 border border-slate-200 shadow-xs">
          {/* Header with Title and Mode Switchers */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-4">
            <div>
              <div className="flex items-center gap-2.5">
                <BarChart3 className="size-4.5 text-red-600" />
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Portfolio Sales Velocity & Deterministic Unit Economics
                </h3>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-bold">
                  SP-API AUDITED
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Multi-metric reconciliation across Amazon SP-API settlements, FBA pick/pack fees, and
                ad spend
              </p>
            </div>

            {/* View Mode Tabs + Time Range Controls */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Metric View Tabs */}
              <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-mono">
                {[
                  { key: 'REVENUE_PROFIT', label: 'GMV & Net Profit' },
                  { key: 'VELOCITY_UNITS', label: 'Units & Velocity' },
                  { key: 'TACOS_SPEND', label: 'PPC & TACoS' },
                  { key: 'BUYBOX_RADAR', label: 'Buy Box & Attacks' },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setChartMetric(tab.key as any)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg font-semibold transition-all cursor-pointer text-[11px]',
                      chartMetric === tab.key
                        ? 'bg-white text-red-700 border border-slate-200 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900',
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Time Range Selector */}
              <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-mono">
                {(['Today', '7D', '14D', '30D', '90D'] as const).map((r) => (
                  <button
                    key={r}
                    onClick={() => setTimeRange(r)}
                    className={cn(
                      'px-2.5 py-1 rounded-lg font-semibold transition-all cursor-pointer',
                      timeRange === r
                        ? 'bg-white text-red-700 border border-slate-200 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900',
                    )}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Dynamic Recharts Multi-Mode Container */}
          <div className="h-80 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              {chartMetric === 'REVENUE_PROFIT' ? (
                <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="glowGmv" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#DC2626" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#DC2626" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="glowProfit" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#16A34A" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#16A34A" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                    tickFormatter={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      const margin = ((d.profit / d.revenue) * 100).toFixed(1)
                      return (
                        <div className="rounded-xl bg-white border border-slate-200 p-3.5 shadow-lg font-mono text-xs space-y-2 min-w-[210px]">
                          <div className="text-slate-900 font-bold border-b border-slate-100 pb-1 flex items-center justify-between">
                            <span>{d.date}</span>
                            <span className="text-[10px] text-slate-500">SP-API Reconciled</span>
                          </div>
                          <div className="flex items-center justify-between text-slate-900">
                            <span>Gross GMV:</span>
                            <span className="font-bold font-mono">${d.revenue.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center justify-between text-emerald-700">
                            <span>Net Contribution:</span>
                            <span className="font-bold font-mono">${d.profit.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center justify-between text-slate-500 text-[11px]">
                            <span>Amazon FBA Fees (15%):</span>
                            <span>-${d.fbaFee.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center justify-between text-slate-500 text-[11px]">
                            <span>PPC Ad Spend:</span>
                            <span>-${d.adSpend.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center justify-between text-slate-700 text-[11px] pt-1.5 border-t border-slate-100 font-semibold">
                            <span>Units: {d.units}</span>
                            <span className="text-emerald-700">{margin}% Margin</span>
                          </div>
                        </div>
                      )
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#DC2626"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#glowGmv)"
                    name="Gross Sales"
                  />
                  <Area
                    type="monotone"
                    dataKey="profit"
                    stroke="#16A34A"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#glowProfit)"
                    name="Net Profit"
                  />
                </AreaChart>
              ) : chartMetric === 'VELOCITY_UNITS' ? (
                <ComposedChart
                  data={trendData}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="glowBar" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#DC2626" stopOpacity={0.8} />
                      <stop offset="100%" stopColor="#B91C1C" stopOpacity={0.3} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div className="rounded-xl bg-white border border-slate-200 p-3.5 shadow-lg font-mono text-xs space-y-1.5 min-w-[190px]">
                          <div className="text-slate-900 font-bold border-b border-slate-100 pb-1">
                            {d.date} · Units Sold
                          </div>
                          <div className="flex items-center justify-between text-red-600">
                            <span>Units Shipped:</span>
                            <span className="font-bold">{d.units} units</span>
                          </div>
                          <div className="flex items-center justify-between text-slate-600 text-[11px]">
                            <span>Avg Price / Order:</span>
                            <span>${(d.revenue / d.units).toFixed(2)}</span>
                          </div>
                        </div>
                      )
                    }}
                  />
                  <Bar
                    dataKey="units"
                    fill="url(#glowBar)"
                    radius={[6, 6, 0, 0]}
                    name="Daily Units"
                  />
                  <Line
                    type="monotone"
                    dataKey="units"
                    stroke="#475569"
                    strokeWidth={2}
                    dot={{ fill: '#475569', r: 3 }}
                  />
                </ComposedChart>
              ) : chartMetric === 'TACOS_SPEND' ? (
                <ComposedChart
                  data={trendData}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="glowAds" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#475569" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#475569" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                    tickFormatter={(v) => `$${v}`}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[0, 20]}
                    tick={{ fill: '#D97706', fontSize: 11, fontFamily: 'monospace' }}
                    tickFormatter={(v) => `${v}%`}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div className="rounded-xl bg-white border border-slate-200 p-3.5 shadow-lg font-mono text-xs space-y-1.5 min-w-[200px]">
                          <div className="text-slate-900 font-bold border-b border-slate-100 pb-1">
                            {d.date} · Ad Spend & TACoS
                          </div>
                          <div className="flex items-center justify-between text-slate-800">
                            <span>Amazon PPC Spend:</span>
                            <span className="font-bold">${d.adSpend}</span>
                          </div>
                          <div className="flex items-center justify-between text-amber-700">
                            <span>TACoS %:</span>
                            <span className="font-bold">{d.tacos}%</span>
                          </div>
                          <div className="text-[10.5px] text-slate-500 pt-1 border-t border-slate-100">
                            <span>ROAS: {(d.revenue / (d.adSpend || 1)).toFixed(2)}x Return</span>
                          </div>
                        </div>
                      )
                    }}
                  />
                  <ReferenceLine
                    yAxisId="right"
                    y={12}
                    stroke="#DC2626"
                    strokeDasharray="4 4"
                    label={{ value: '12% TACoS Target Ceiling', fill: '#DC2626', fontSize: 10 }}
                  />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="adSpend"
                    stroke="#475569"
                    strokeWidth={2}
                    fill="url(#glowAds)"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="tacos"
                    stroke="#D97706"
                    strokeWidth={2.5}
                    dot={{ fill: '#D97706', r: 3 }}
                  />
                </ComposedChart>
              ) : (
                <ComposedChart
                  data={trendData}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="left"
                    domain={[85, 100]}
                    tick={{ fill: '#16A34A', fontSize: 11, fontFamily: 'monospace' }}
                    tickFormatter={(v) => `${v}%`}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[0, 15]}
                    tick={{ fill: '#DC2626', fontSize: 11, fontFamily: 'monospace' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div className="rounded-xl bg-white border border-slate-200 p-3.5 shadow-lg font-mono text-xs space-y-1.5 min-w-[210px]">
                          <div className="text-slate-900 font-bold border-b border-slate-100 pb-1">
                            {d.date} · Buy Box Correlation
                          </div>
                          <div className="flex items-center justify-between text-emerald-700">
                            <span>Buy Box Win Rate:</span>
                            <span className="font-bold">{d.buyBoxRate}%</span>
                          </div>
                          <div className="flex items-center justify-between text-red-600">
                            <span>Rival Price Undercuts:</span>
                            <span className="font-bold">{d.competitorAttacks} attacks</span>
                          </div>
                          <div className="text-[10.5px] text-slate-500 pt-1 border-t border-slate-100">
                            <span>Copilot Repricer Defended: 100% Intact</span>
                          </div>
                        </div>
                      )
                    }}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="buyBoxRate"
                    stroke="#16A34A"
                    strokeWidth={2.5}
                    dot={{ fill: '#16A34A', r: 3 }}
                  />
                  <Bar
                    yAxisId="right"
                    dataKey="competitorAttacks"
                    fill="#DC2626"
                    opacity={0.4}
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              )}
            </ResponsiveContainer>
          </div>

          {/* Chart Legend & Summary Telemetry Footer */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-100 mt-3 text-xs font-mono">
            <div className="flex flex-wrap items-center gap-5">
              <span className="flex items-center gap-2 text-slate-700">
                <span className="size-2.5 rounded-full bg-red-600 shadow-xs" />
                Gross Sales (GMV)
              </span>
              <span className="flex items-center gap-2 text-slate-700">
                <span className="size-2.5 rounded-full bg-emerald-600 shadow-xs" />
                Net Margin ({avgMargin.toFixed(1)}%)
              </span>
              <span className="flex items-center gap-2 text-slate-700">
                <span className="size-2.5 rounded-full bg-slate-600 shadow-xs" />
                TACoS ({avgTacos.toFixed(1)}%)
              </span>
            </div>
            <div className="flex items-center gap-4 text-slate-500 text-[11px]">
              <span>Avg Daily Run Rate: ${(totalPeriodRevenue / (trendData.length || 1)).toFixed(0)}</span>
              <span>·</span>
              <span className="text-emerald-700 font-semibold">100% SP-API In-Sync</span>
            </div>
          </div>
        </div>

        {/* Section: Buy Box Defense Radar & 1-Click Action Queue */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Buy Box Win Radar Gauge Card (7 cols) */}
          <div className="lg:col-span-7 rounded-2xl bg-white p-5 sm:p-6 border border-slate-200 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Zap className="size-4 text-red-600" />
                  <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                    Buy Box Win Radar & Real-Time Defense
                  </h3>
                </div>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-bold">
                  94.6% DOMINANT
                </span>
              </div>

              {/* Radial Progress Display with Animated SVG */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-center my-2">
                <div className="relative flex flex-col items-center justify-center">
                  <div className="relative size-36 flex items-center justify-center">
                    <svg className="size-full -rotate-90" viewBox="0 0 100 100">
                      <defs>
                        <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#DC2626" />
                          <stop offset="100%" stopColor="#B91C1C" />
                        </linearGradient>
                      </defs>
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#F1F5F9"
                        strokeWidth="9"
                      />
                      <motion.circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="url(#gaugeGrad)"
                        strokeWidth="9"
                        strokeDasharray={2 * Math.PI * 40}
                        initial={{ strokeDashoffset: 2 * Math.PI * 40 }}
                        animate={{ strokeDashoffset: 2 * Math.PI * 40 * (1 - 0.946) }}
                        transition={{ duration: 1.4, ease: 'easeOut' }}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <NumberTicker
                        value={94.6}
                        decimals={1}
                        suffix="%"
                        className="text-2xl font-mono font-bold text-slate-900"
                      />
                      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                        Win Rate
                      </span>
                    </div>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-2 text-center">
                    Zero suppressed listings detected across 48 monitored ASINs.
                  </span>
                </div>

                {/* Category Breakdown Bars */}
                <div className="space-y-3 font-mono text-xs">
                  <div>
                    <div className="flex items-center justify-between text-slate-700 mb-1">
                      <span>Electronics & Audio</span>
                      <span className="text-red-700 font-bold">96.8%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-red-600 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: '96.8%' }}
                        transition={{ duration: 1, delay: 0.2 }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-slate-700 mb-1">
                      <span>Home & Kitchen</span>
                      <span className="text-slate-800 font-bold">92.4%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-slate-700 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: '92.4%' }}
                        transition={{ duration: 1, delay: 0.3 }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-slate-700 mb-1">
                      <span>Fitness & Outdoors</span>
                      <span className="text-emerald-700 font-bold">95.2%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-emerald-600 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: '95.2%' }}
                        transition={{ duration: 1, delay: 0.4 }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Real-Time Competitor Price Feed */}
              <div className="mt-4 pt-3 border-t border-slate-100 space-y-2.5">
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block mb-1">
                  Active Competitor Threat Interceptions:
                </span>
                {competitorAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition-all text-xs"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">
                          {alert.sku}
                        </span>
                        <span className="font-semibold text-slate-900 truncate max-w-[170px] sm:max-w-xs">
                          {alert.title}
                        </span>
                      </div>
                      <span className="font-mono text-[10.5px] text-slate-500">{alert.time}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] pt-1">
                      <span className="text-slate-600">{alert.action}</span>
                      <span className="text-emerald-700 font-semibold font-mono">
                        ✓ {alert.response}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 mt-4 flex items-center justify-between">
              <span className="text-slate-500 font-mono text-[11px]">
                Under-cutting defense latency: &lt; 48ms
              </span>
              <Link to="/pricing-lab">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs font-mono border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl"
                >
                  Adjust Repricing Guardrails →
                </Button>
              </Link>
            </div>
          </div>

          {/* Right: 1-Click Action Queue */}
          <div className="relative lg:col-span-5 rounded-2xl bg-white p-5 sm:p-6 border border-slate-200 shadow-xs flex flex-col justify-between overflow-hidden">
            <div>
              <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Inbox className="size-4 text-red-600" />
                  <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                    Action Execution Queue
                  </h3>
                </div>
                <span className="font-mono text-xs text-red-700 bg-red-50 px-2 py-0.5 rounded-full border border-red-200 font-bold">
                  {pendingActionsCount} Pending
                </span>
              </div>

              <p className="text-xs text-slate-500 mb-3">
                Autonomous proposals awaiting one-click human confirmation before SP-API submission:
              </p>

              <div className="space-y-3">
                {pendingActions.slice(0, 3).map((act: any) => (
                  <div
                    key={act.id}
                    className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition-all text-xs shadow-2xs"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono font-bold text-[10.5px] uppercase tracking-wider text-red-700">
                        {act.action_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">Ready</span>
                    </div>
                    <p className="font-semibold text-slate-900 line-clamp-1">{act.title}</p>
                    <p className="text-slate-500 text-[11px] mt-0.5 line-clamp-1">
                      {act.description}
                    </p>

                    <div className="mt-3 pt-2.5 border-t border-slate-200 flex items-center justify-between gap-2">
                      <ShimmerButton
                        variant="red"
                        size="sm"
                        onClick={() => handleApproveAction(act.id)}
                        disabled={approvingId === act.id}
                      >
                        {approvingId === act.id ? (
                          <RefreshCw className="size-3 animate-spin" />
                        ) : (
                          <CheckCircle2 className="size-3" />
                        )}
                        <span>Approve & Push to SP-API</span>
                      </ShimmerButton>
                      <button
                        onClick={() => navigate('/actions')}
                        className="text-[11px] font-mono text-slate-600 hover:text-slate-900"
                      >
                        Inspect →
                      </button>
                    </div>
                  </div>
                ))}

                {pendingActionsCount === 0 && (
                  <div className="p-8 text-center rounded-xl bg-slate-50 border border-slate-200">
                    <CheckCircle2 className="size-8 text-emerald-600 mx-auto mb-2" />
                    <span className="text-xs font-semibold text-slate-700 block">
                      Queue fully synchronized!
                    </span>
                    <span className="text-[11px] text-slate-500 mt-1 block">
                      No automated exceptions pending approval.
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200 mt-4">
              <Link to="/actions" className="w-full block">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs font-mono border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl"
                >
                  Open Action Center ({pendingActionsCount}) →
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Section: AI Product Research & Listing Intelligence Hub */}
        <div className="rounded-2xl bg-white p-5 sm:p-6 border border-slate-200 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="size-4.5 text-red-600" />
                <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
                  <span>AI Product Research & Listing Intelligence</span>
                  <span className="font-mono text-[9.5px] px-2 py-0.2 rounded bg-red-50 text-red-700 border border-red-200 font-bold uppercase">
                    GEMINI 2.0 FLASH
                  </span>
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Continuous review sentiment mining, competitor gap discovery, and search indexing recommendations
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-slate-500">Catalog Health Index:</span>
              <strong className="text-emerald-700 font-bold text-sm">96.2% Nominal</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {listingIntelligence.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition-all text-xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">
                      {item.sku}
                    </span>
                    <span
                      className={cn(
                        'text-[9.5px] font-mono font-bold uppercase px-1.5 py-0.2 rounded',
                        item.status === 'RECOMMENDED' && 'bg-red-50 text-red-700 border border-red-200',
                        item.status === 'READY_TO_SYNC' && 'bg-emerald-50 text-emerald-700 border border-emerald-200',
                        item.status === 'ACTIVE_GUARD' && 'bg-blue-50 text-blue-700 border border-blue-200',
                      )}
                    >
                      {item.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <h4 className="font-semibold text-slate-900 text-xs">{item.title}</h4>
                  <p className="text-[10.5px] text-slate-500 mt-0.5 font-mono">{item.category}</p>

                  <div className="p-2.5 rounded-lg bg-white border border-slate-200 mt-2.5 shadow-2xs">
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 mb-1">
                      <span>Gemini Market Synthesis</span>
                      <span className="text-red-600 font-semibold">{item.signalType.replace(/_/g, ' ')}</span>
                    </div>
                    <p className="text-[11px] text-slate-700 leading-relaxed">{item.insight}</p>
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-slate-200 flex items-center justify-between font-mono text-[11px]">
                  <span className="text-slate-500">Projected Impact:</span>
                  <span className="text-emerald-700 font-bold">{item.impact}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section: Inventory Velocity & Amazon FBA Restock Runway */}
        <div className="rounded-2xl bg-white p-5 sm:p-6 border border-slate-200 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <Boxes className="size-4 text-red-600" />
                <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                  Inventory Velocity & Stockout Risk Breakdown
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Predictive runout rates based on 30-day sales velocity and Amazon inbound logistics
              </p>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-mono">
              {[
                { label: 'All Portfolio', val: 'ALL' },
                { label: `Hazard (${stockoutRiskCount})`, val: 'STOCKOUT_RISK' },
                { label: `Healthy (${healthyCount})`, val: 'HEALTHY' },
                { label: `Overstock (${overstockCount})`, val: 'OVERSTOCK' },
              ].map((f) => (
                <button
                  key={f.val}
                  onClick={() => setSelectedInventoryFilter(f.val)}
                  className={cn(
                    'px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer',
                    selectedInventoryFilter === f.val
                      ? 'bg-white text-red-700 font-semibold border border-slate-200 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900',
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Segmented Color Bar */}
          <div className="space-y-3">
            <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
              <div
                className="bg-emerald-600 h-full transition-all duration-500"
                style={{
                  width: `${Math.max(10, (healthyCount / (activeSkus || 1)) * 100)}%`,
                }}
                title={`Healthy: ${healthyCount} SKUs`}
              />
              <div
                className="bg-amber-500 h-full transition-all duration-500"
                style={{
                  width: `${Math.max(5, (stockoutRiskCount / (activeSkus || 1)) * 100)}%`,
                }}
                title={`Stockout Risk: ${stockoutRiskCount} SKUs`}
              />
              <div
                className="bg-red-600 h-full transition-all duration-500"
                style={{
                  width: `${Math.max(5, (overstockCount / (activeSkus || 1)) * 100)}%`,
                }}
                title={`Overstock: ${overstockCount} SKUs`}
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 font-mono text-xs text-slate-600">
              <div className="flex flex-wrap items-center gap-5">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-emerald-600" />
                  Healthy Velocity: <strong className="text-slate-900">{healthyCount}</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-amber-500" />
                  Stockout Hazard (&lt;14d):{' '}
                  <strong className="text-amber-700">{stockoutRiskCount}</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-red-600" />
                  Overstock (&gt;90d): <strong className="text-red-700">{overstockCount}</strong>
                </span>
              </div>
              <span className="text-[11px] text-slate-500">
                Total SKUs Monitored: {productList.length}
              </span>
            </div>
          </div>
        </div>

        {/* Section: Searchable Catalog Attention Rankings Table */}
        <div className="rounded-2xl bg-white p-5 sm:p-6 border border-slate-200 shadow-xs">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <Flame className="size-4 text-red-600" />
                <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                  Catalog Attention Rankings & Live Portfolio Monitor
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Ranked by multi-dimensional risk score (stockout urgency, pricing pressure, review spikes)
              </p>
            </div>

            {/* Instant Search Bar & Category Filter */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="size-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter by SKU or title…"
                  className="pl-8 pr-3 py-1.5 bg-slate-50 rounded-xl border border-slate-200 text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 w-48 sm:w-60"
                />
              </div>

              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-1.5 bg-slate-50 rounded-xl border border-slate-200 text-xs font-mono text-slate-700 focus:outline-none focus:border-red-500 cursor-pointer"
              >
                {availableCategories.map((c) => (
                  <option key={c} value={c}>
                    {c === 'ALL' ? 'All Categories' : c}
                  </option>
                ))}
              </select>

              <Link
                to="/products"
                className="text-xs font-mono font-semibold text-red-600 hover:text-red-700 transition-colors"
              >
                Full Catalog ({productList.length}) →
              </Link>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-semibold text-[10px] tracking-wider">
                <tr>
                  <th className="p-3.5">Product Name & ASIN</th>
                  <th className="p-3.5">Category</th>
                  <th className="p-3.5">Base Price</th>
                  <th className="p-3.5">Inventory State</th>
                  <th className="p-3.5">Pricing Status</th>
                  <th className="p-3.5">Risk Score</th>
                  <th className="p-3.5 text-right">Workspace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {topAttention.map((p) => (
                  <tr
                    key={p.product_id}
                    className="hover:bg-slate-50/80 transition-colors group"
                  >
                    <td className="p-3.5 font-medium text-slate-900 max-w-xs">
                      <Link
                        to={`/products/${encodeURIComponent(p.product_id)}`}
                        className="hover:text-red-600 transition-colors block truncate"
                        title={p.name}
                      >
                        {p.name}
                      </Link>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {p.product_id}
                      </span>
                    </td>
                    <td className="p-3.5 text-slate-600">{p.category}</td>
                    <td className="p-3.5 font-bold font-mono text-slate-900">${p.base_price.toFixed(2)}</td>
                    <td className="p-3.5">
                      <span
                        className={cn(
                          'px-2 py-0.5 rounded text-[10px] font-bold tracking-tight',
                          p.inventory_category === 'STOCKOUT_RISK' &&
                            'bg-red-50 text-red-700 border border-red-200',
                          p.inventory_category === 'LOW_COVER' &&
                            'bg-amber-50 text-amber-700 border border-amber-200',
                          p.inventory_category === 'HEALTHY' &&
                            'bg-emerald-50 text-emerald-700 border border-emerald-200',
                          p.inventory_category === 'OVERSTOCK' &&
                            'bg-slate-100 text-slate-700 border border-slate-200',
                          !p.inventory_category &&
                            'bg-slate-100 text-slate-600 border border-slate-200',
                        )}
                      >
                        {p.inventory_category || 'HEALTHY'}
                      </span>
                    </td>
                    <td className="p-3.5 text-[11px] text-slate-600">
                      {p.price_state || 'HEALTHY_RANGE'}
                    </td>
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'font-bold',
                            (p.attention_score || 0) > 70
                              ? 'text-red-600'
                              : (p.attention_score || 0) > 40
                              ? 'text-amber-600'
                              : 'text-emerald-700',
                          )}
                        >
                          {p.attention_score || 0}/100
                        </span>
                      </div>
                    </td>
                    <td className="p-3.5 text-right">
                      <Link
                        to={`/products/${encodeURIComponent(p.product_id)}`}
                        className="inline-flex items-center gap-1 text-red-600 hover:text-red-700 font-semibold"
                      >
                        <span>Open</span>
                        <ChevronRight className="size-3" />
                      </Link>
                    </td>
                  </tr>
                ))}

                {topAttention.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-slate-500 font-mono text-xs">
                      No matching products found for query "{searchQuery}".
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </AppShell>
  )
}
