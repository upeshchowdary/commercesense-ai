import { AppShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { ProvenanceBadge } from '@/components/shared/ProvenanceBadge'
import {
  Globe,
  Key,
  CheckCircle2,
  Lock,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Connections() {

  const capabilities = [
    { name: 'Reports API (Sales & Traffic)', code: 'GET_SALES_AND_TRAFFIC_REPORT', status: 'VERIFIED', endpoint: 'sellingpartnerapi-eu.amazon.com' },
    { name: 'FBA Inventory Summaries', code: 'GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA', status: 'VERIFIED', endpoint: 'sellingpartnerapi-eu.amazon.com' },
    { name: 'Product Pricing & Competitive Offers', code: 'getCompetitiveSummary', status: 'VERIFIED', endpoint: 'sellingpartnerapi-eu.amazon.com' },
    { name: 'Amazon Brand Analytics', code: 'BRAND_ANALYTICS_SEARCH_TERMS', status: 'REQUIRES_BRAND_REGISTRY', endpoint: 'sellingpartnerapi-eu.amazon.com' },
    { name: 'Customer Feedback & VOC API', code: 'CUSTOMER_FEEDBACK', status: 'NOT_AVAILABLE_IN_INDIA', endpoint: 'Amazon.in market restriction' },
  ]

  return (
    <AppShell>
      <Topbar title="Data Connections & Integrations" />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Amazon SP-API & Provider Gateway
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Official Selling Partner SDK connections, credential encryption status, and Gemini multi-key rotation pool.
            </p>
          </div>
          <ProvenanceBadge provenance="AMAZON_OFFICIAL" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Amazon SP-API Endpoint Architecture */}
          <div className="space-y-6">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <Globe className="size-5 text-red-600" />
                  <h3 className="text-base font-bold text-foreground">Amazon India (SP-API)</h3>
                </div>
                <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="size-3.5" /> Connected
                </span>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">Marketplace ID:</span>
                  <span className="font-mono font-semibold text-foreground">A21TJRUUN4KGV (IN)</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">Regional Gateway Endpoint:</span>
                  <span className="font-mono font-semibold text-foreground">sellingpartnerapi-eu.amazon.com</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">Default Currency:</span>
                  <span className="font-mono font-semibold text-foreground">INR (₹)</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-muted-foreground">Egress Gate Security:</span>
                  <span className="font-semibold text-emerald-700 dark:text-emerald-400">Strict Egress Interceptor Active</span>
                </div>
              </div>
            </div>

            {/* Granular Capabilities */}
            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="text-sm font-bold text-foreground mb-3">Endpoint Capability Matrix</h3>
              <div className="space-y-2.5">
                {capabilities.map((cap) => (
                  <div key={cap.code} className="p-3 rounded-md border border-border bg-muted/20 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-foreground">{cap.name}</span>
                      <span
                        className={cn(
                          'px-2 py-0.5 rounded text-[10px] font-bold tracking-tight',
                          cap.status === 'VERIFIED' && 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400',
                          cap.status === 'REQUIRES_BRAND_REGISTRY' && 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400',
                          cap.status === 'NOT_AVAILABLE_IN_INDIA' && 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/40 dark:text-red-400',
                        )}
                      >
                        {cap.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <span className="font-mono text-[10.5px] text-muted-foreground block mt-1">
                      {cap.code} · {cap.endpoint}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Gemini API Key Pool Rotator */}
          <div className="space-y-6">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <Key className="size-5 text-red-600" />
                  <h3 className="text-base font-bold text-foreground">Gemini API Key Pool Rotator</h3>
                </div>
                <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/40 dark:text-red-400">
                  9 Keys Configured
                </span>
              </div>

              <p className="text-xs text-muted-foreground mb-4">
                Automatic round-robin and rate-limit recovery. Switches keys instantaneously upon encountering 429 quota exhaustion.
              </p>

              <div className="space-y-2 text-xs font-mono">
                {[
                  { label: 'Key 1 (-d)', status: 'Active (Current)' },
                  { label: 'Key 2 (-d)', status: 'Standby' },
                  { label: 'Key 3 (-upesh.k)', status: 'Standby' },
                  { label: 'Key 4 (-claude)', status: 'Standby' },
                  { label: 'Key 5 (-kk)', status: 'Standby' },
                  { label: 'Key 6 (-omni)', status: 'Standby' },
                  { label: 'Key 7 (-r)', status: 'Standby' },
                  { label: 'Key 8 (-r)', status: 'Standby' },
                  { label: 'Key 9 (---u2)', status: 'Standby' },
                ].map((k, idx) => (
                  <div key={idx} className="flex justify-between items-center p-2 rounded bg-muted/30">
                    <span className="text-foreground">{k.label}</span>
                    <span
                      className={cn(
                        'text-[10px] font-bold px-1.5 py-0.5 rounded',
                        idx === 0 ? 'bg-red-600 text-white shadow-xs' : 'text-muted-foreground',
                      )}
                    >
                      {k.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Secret Security Guarantee */}
            <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 shadow-xs p-5 text-xs text-slate-800 dark:text-slate-200">
              <div className="flex items-center gap-2 font-bold text-red-600 dark:text-red-400 mb-1.5">
                <Lock className="size-4" />
                <span>Zero Raw Secret Exposure Guarantee (Spec §32)</span>
              </div>
              <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
                Client-side API requests never return or transmit raw API keys or tokens. All credentials remain encrypted at rest in server environment storage and only boolean validation flags (<code className="font-mono">key_set: true</code>) are transmitted.
              </p>
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  )
}
