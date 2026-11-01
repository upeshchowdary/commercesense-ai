import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import { getMarketRadarTopics, getMarketRadarNews } from '@/lib/api'
import {
  TrendingUp,
  Newspaper,
  Search,
  ExternalLink,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function MarketRadar() {
  const [activeTab, setActiveTab] = useState<'TOPICS' | 'NEWS' | 'RECALLS'>('TOPICS')
  const [searchQuery, setSearchQuery] = useState('')

  const { data: topics = [], isLoading: topicsLoading } = useQuery({
    queryKey: ['market_radar_topics'],
    queryFn: getMarketRadarTopics,
  })

  const { data: news = [], isLoading: newsLoading } = useQuery({
    queryKey: ['market_radar_news'],
    queryFn: getMarketRadarNews,
  })

  const topicList: any[] = Array.isArray(topics) ? topics : ((topics as any)?.topics ?? [])
  const newsList: any[] = (news as any)?.articles
    ? (news as any).articles
    : Array.isArray(news)
    ? news
    : []

  const filteredTopics = topicList.filter((t: any) =>
    (t.keyword || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.category || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredNews = newsList.filter((n: any) =>
    (n.title || n.headline || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (n.domain || n.source || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <AppShell>
      <Topbar title="Market Radar" />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Macro Demand Signals & Regulatory Radar
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Zero paid web scrapers. Live stream combines GDELT 2.0 public doc feed, CPSC product safety RSS, and Amazon Brand Analytics.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ProvenanceBadge provenance="PUBLIC_NEWS" />
            <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
          </div>
        </div>

        {/* Search & Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2 border-b border-border overflow-x-auto pb-px">
            {[
              { id: 'TOPICS', label: `Trend Momentum (${topicList.length})`, icon: TrendingUp },
              { id: 'NEWS', label: `Public News Stream (${newsList.length})`, icon: Newspaper },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={cn(
                  'flex items-center gap-2 px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap',
                  activeTab === tab.id
                    ? 'border-red-600 text-red-600 dark:border-red-500 dark:text-red-400'
                    : 'border-transparent text-slate-500 hover:text-slate-900 dark:text-slate-400',
                )}
              >
                <tab.icon className="size-3.5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter topics or news..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-border rounded-md bg-card text-foreground"
            />
          </div>
        </div>

        {/* Content */}
        {activeTab === 'TOPICS' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {topicsLoading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="h-36 rounded-lg border border-border bg-card animate-pulse" />
              ))
            ) : filteredTopics.length === 0 ? (
              <div className="col-span-full p-8 text-center text-xs text-muted-foreground border border-dashed rounded-lg bg-card">
                No market trends matching query.
              </div>
            ) : (
              filteredTopics.map((topic: any) => (
                <div
                  key={topic.keyword}
                  className="rounded-lg border border-border bg-card p-4 hover:shadow-xs transition-shadow flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-red-700 bg-red-50 border border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900/50 px-2 py-0.5 rounded">
                        {topic.category}
                      </span>
                      <div className="flex items-center gap-1 font-semibold text-xs text-foreground">
                        {topic.trajectory === 'SURGING' || topic.direction === 'HEATING' ? (
                          <ArrowUpRight className="size-4 text-emerald-600" />
                        ) : topic.trajectory === 'DECLINING' || topic.direction === 'COOLING' ? (
                          <ArrowDownRight className="size-4 text-red-600" />
                        ) : (
                          <Minus className="size-4 text-slate-400" />
                        )}
                        <span>{topic.trajectory || topic.direction || 'STABLE'}</span>
                      </div>
                    </div>

                    <h3 className="text-base font-semibold text-foreground tracking-tight">
                      {topic.keyword}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      Momentum Score: {topic.momentum_score}/100 {topic.drivers ? `• ${topic.drivers.join(', ')}` : `based on ${topic.news_count || 10} public observations.`}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="font-mono">Category: {topic.category}</span>
                    <ProvenanceBadge provenance="PUBLIC_NEWS" className="text-[9px] py-0" />
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {newsLoading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="h-24 rounded-lg border border-border bg-card animate-pulse" />
              ))
            ) : filteredNews.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground border border-dashed rounded-lg bg-card">
                No news articles found.
              </div>
            ) : (
              filteredNews.map((article: any, idx: number) => (
                <div
                  key={article.url || article.id || idx}
                  className="rounded-lg border border-border bg-card p-4 hover:shadow-xs transition-shadow flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-semibold text-xs text-red-700">{article.domain || article.source || 'GDELT News'}</span>
                      <span className="text-muted-foreground text-xs">·</span>
                      <span className="text-xs text-muted-foreground">
                        {article.seendate ? article.seendate.slice(0, 8) : (article.published_at ? new Date(article.published_at).toLocaleDateString() : 'Recent')}
                      </span>
                      <ProvenanceBadge provenance="PUBLIC_NEWS" className="text-[9.5px] py-0" />
                    </div>

                    <h4 className="text-sm font-semibold text-foreground leading-snug">
                      {article.title || article.headline}
                    </h4>
                    {article.summary && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {article.summary}
                      </p>
                    )}
                  </div>
                  {article.url && (
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-600 hover:text-red-700 hover:underline shrink-0"
                    >
                      <span>Read Source</span>
                      <ExternalLink className="size-3.5" />
                    </a>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </AppShell>
  )
}
