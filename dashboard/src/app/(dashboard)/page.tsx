'use client'

import { useRouter } from 'next/navigation'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { formatCurrency, formatCurrencyCompact } from '@/lib/formatters'
import { useAnalytics } from '@/hooks/useAnalytics'
import { KPICard } from '@/components/analytics/KPICard'
import { AlertPanel } from '@/components/AlertPanel'
import {
  DollarSign, Users, TrendingUp, ShoppingBag, ChevronRight, Star, UserCheck,
} from 'lucide-react'

interface OverviewData {
  total_gmv: number
  total_views: number
  total_creators: number
  global_conversion_rate: number
  total_buyers: number
  top_creator_name: string
  top_creator_revenue: number
  top_product_name: string
  top_product_gmv: number
}

interface CreatorItem {
  id: string
  name: string
  estimated_revenue: number
  total_views: number
  creator_type: string
  content_categories: string[]
  has_whatsapp: boolean
}

interface ContentItem {
  id: string
  creator_name: string
  product_name: string | null
  views: number
  engagement_rate: number
  gmv_generated: number
}

interface ProductItem {
  id: string
  name: string
  total_gmv: number
  total_creators: number
  conversion_rate: number
}

export default function DashboardPage() {
  const router = useRouter()
  const { data: overview, loading: overviewLoading } = useAnalytics<OverviewData>('overview')
  const { data: creatorsData, loading: creatorsLoading } = useAnalytics<CreatorItem[]>('creators', { sort_by: 'revenue', limit: 20 })
  const { data: contentData, loading: contentLoading } = useAnalytics<ContentItem[]>('content', { sort_by: 'views', limit: 5 })
  const { data: productsData, loading: productsLoading } = useAnalytics<ProductItem[]>('products', { sort_by: 'gmv', limit: 5 })

  const creators = creatorsData ?? []
  const content = contentData ?? []
  const products = productsData ?? []
  const isLoading = overviewLoading

  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Selamat pagi' : now.getHours() < 17 ? 'Selamat siang' : 'Selamat malam'

  // Creator type breakdown
  const typeCount: Record<string, number> = {}
  creators.forEach(c => {
    const t = c.creator_type || 'affiliator'
    typeCount[t] = (typeCount[t] || 0) + 1
  })
  const totalCreatorsFetched = creators.length || 1
  const withWhatsapp = creators.filter(c => c.has_whatsapp).length

  // Top categories
  const categoryCount: Record<string, number> = {}
  creators.forEach(c => {
    (c.content_categories ?? []).forEach(cat => {
      categoryCount[cat] = (categoryCount[cat] || 0) + 1
    })
  })
  const topCategories = Object.entries(categoryCount).sort((a, b) => b[1] - a[1]).slice(0, 5)

  // Chart data from top creators
  const revenueChartData = creators.slice(0, 8).map(c => ({
    name: c.name.split(' ')[0],
    revenue: c.estimated_revenue,
    views: c.total_views,
  }))

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">{greeting} 👋</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {now.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-green-900/20 border border-green-900/30 px-3 py-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-green-400">Sistem Aktif</span>
        </div>
      </div>

      {/* Primary KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <KPICard 
          title="Total GMV" 
          icon={DollarSign}
          value={overview ? formatCurrencyCompact(overview.total_gmv) : '—'}
          isLoading={isLoading}
          onClick={() => router.push('/revenue-insights')} 
        />
        <KPICard 
          title="Total Buyers" 
          icon={UserCheck}
          value={overview ? overview.total_buyers.toLocaleString('id-ID') : '—'}
          isLoading={isLoading}
          onClick={() => router.push('/revenue-insights')} 
        />
        <KPICard 
          title="Total Affiliator" 
          icon={Users}
          value={overview ? overview.total_creators.toString() : '—'}
          isLoading={isLoading}
          onClick={() => router.push('/creator-intelligence')} 
        />
        <KPICard 
          title="Global Conversion Rate" 
          icon={TrendingUp}
          value={overview ? `${overview.global_conversion_rate.toFixed(2)}%` : '—'}
          isLoading={isLoading} 
        />
      </div>

      {/* Alerts */}
      <AlertPanel />

      {/* Top Highlights */}
      {overview && !isLoading && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Top Affiliator', value: overview.top_creator_name || '—', sub: formatCurrency(overview.top_creator_revenue), icon: Star, color: 'text-yellow-400', href: '/creator-intelligence' },
            { label: 'Top Product', value: overview.top_product_name || '—', sub: `GMV: ${formatCurrency(overview.top_product_gmv)}`, icon: ShoppingBag, color: 'text-violet-400', href: '/product-analytics' },
            { label: 'Total Buyers', value: overview.total_buyers.toLocaleString('id-ID'), sub: 'dari semua konten', icon: Users, color: 'text-blue-400', href: '/revenue-insights' },
          ].map(h => (
            <div key={h.label} onClick={() => router.push(h.href)}
              className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4 cursor-pointer hover:border-[#2f2f2f] transition-colors flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-[#1a1a1a] flex items-center justify-center shrink-0">
                <h.icon className={`h-5 w-5 ${h.color}`} />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-gray-500">{h.label}</p>
                <p className="text-sm font-semibold text-white truncate">{h.value}</p>
                <p className="text-xs text-gray-600">{h.sub}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Creator Type Breakdown */}
      {!isLoading && creators.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Distribusi Tipe Affiliator */}
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Distribusi Tipe Affiliator</h2>
              <button onClick={() => router.push('/creator-intelligence')}
                className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
                Lihat semua <ChevronRight className="h-3 w-3" />
              </button>
            </div>
            <div className="space-y-3">
              {Object.entries(typeCount).length === 0 ? (
                <p className="text-sm text-gray-600 text-center py-4">Belum ada data</p>
              ) : (
                Object.entries(typeCount)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, count]) => {
                    const colorMap: Record<string, { bar: string; text: string }> = {
                      affiliator: { bar: 'bg-green-500', text: 'text-green-400' },
                      influencer: { bar: 'bg-violet-500', text: 'text-violet-400' },
                      hybrid: { bar: 'bg-teal-500', text: 'text-teal-400' },
                    }
                    const color = colorMap[type] ?? { bar: 'bg-gray-500', text: 'text-gray-400' }
                    const label = type.charAt(0).toUpperCase() + type.slice(1)
                    return (
                      <div key={type}>
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-xs font-medium ${color.text}`}>{label}</span>
                          <span className="text-xs text-gray-500">{count} ({Math.round(count / totalCreatorsFetched * 100)}%)</span>
                        </div>
                        <div className="h-2 rounded-full bg-[#1a1a1a] overflow-hidden">
                          <div className={`h-full rounded-full ${color.bar}`}
                            style={{ width: `${Math.round(count / totalCreatorsFetched * 100)}%` }} />
                        </div>
                      </div>
                    )
                  })
              )}
              {/* WhatsApp availability */}
              <div className="pt-2 mt-2 border-t border-[#1f1f1f] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-green-400" />
                  <span className="text-xs text-gray-400">Tersedia WhatsApp</span>
                </div>
                <span className="text-xs font-semibold text-green-400">
                  {withWhatsapp} / {totalCreatorsFetched} ({Math.round(withWhatsapp / totalCreatorsFetched * 100)}%)
                </span>
              </div>
            </div>
          </div>

          {/* Top Kategori Konten */}
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Top Kategori Konten</h2>
            </div>
            {topCategories.length === 0 ? (
              <p className="text-sm text-gray-600 text-center py-4">Belum ada data kategori</p>
            ) : (
              <div className="space-y-2.5">
                {topCategories.map(([cat, count], i) => (
                  <div key={cat} className="flex items-center gap-3">
                    <span className="text-xs text-gray-600 w-4 shrink-0">#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-white truncate">{cat}</span>
                        <span className="text-xs text-gray-500 ml-2 shrink-0">{count} kreator</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-[#1a1a1a] overflow-hidden">
                        <div className="h-full rounded-full bg-violet-500/60"
                          style={{ width: `${Math.round(count / totalCreatorsFetched * 100)}%` }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue by Creator */}
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Revenue by Affiliator</h2>
            <button onClick={() => router.push('/creator-intelligence')}
              className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
              Lihat semua <ChevronRight className="h-3 w-3" />
            </button>
          </div>
          {isLoading ? <div className="h-48 animate-pulse rounded-lg bg-[#1a1a1a]" /> :
            revenueChartData.length === 0 ? <div className="h-48 flex items-center justify-center text-gray-600 text-sm">Belum ada data</div> : (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={revenueChartData} barSize={24}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false}
                    tickFormatter={v => v >= 1_000_000 ? `${(v/1_000_000).toFixed(0)}M` : v >= 1_000 ? `${(v/1_000).toFixed(0)}K` : v} />
                  <Tooltip contentStyle={{ background: '#111111', border: '1px solid #1f1f1f', borderRadius: 8 }}
                    labelStyle={{ color: '#9ca3af', fontSize: 11 }}
                    formatter={(v: any) => [formatCurrency(v), 'Revenue']} />
                  <Bar dataKey="revenue" fill="#eab308" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
        </div>

        {/* Top Products */}
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f1f1f]">
            <h2 className="text-sm font-semibold text-white">Top Products by GMV</h2>
            <button onClick={() => router.push('/product-analytics')}
              className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
              Lihat semua <ChevronRight className="h-3 w-3" />
            </button>
          </div>
          {isLoading ? (
            <div className="p-4 space-y-3">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-10 animate-pulse rounded-lg bg-[#0d0d0d]" />)}</div>
          ) : products.length === 0 ? (
            <div className="p-8 text-center text-gray-600 text-sm">Belum ada data produk</div>
          ) : (
            <div className="divide-y divide-[#1f1f1f]">
              {products.map((p, i) => (
                <div key={p.id} className="flex items-center justify-between px-5 py-3 hover:bg-[#0d0d0d] transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-xs text-gray-600 w-4 shrink-0">#{i + 1}</span>
                    <div className="min-w-0">
                      <p className="text-white text-sm truncate">{p.name}</p>
                      <p className="text-gray-600 text-xs">{p.total_creators} kreator · {p.conversion_rate.toFixed(1)}% CR</p>
                    </div>
                  </div>
                  <span className="text-yellow-400 font-medium text-sm shrink-0 ml-3">{formatCurrency(p.total_gmv)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Content */}
      <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f1f1f]">
          <h2 className="text-sm font-semibold text-white">Top Content by Views</h2>
          <button onClick={() => router.push('/content-analytics')}
            className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
            Lihat semua <ChevronRight className="h-3 w-3" />
          </button>
        </div>
        {isLoading ? (
          <div className="p-4 space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 animate-pulse rounded-lg bg-[#0d0d0d]" />)}</div>
        ) : content.length === 0 ? (
          <div className="p-8 text-center text-gray-600 text-sm">Belum ada data konten</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
                <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500">Affiliator</th>
                <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500">Produk</th>
                <th className="px-5 py-2.5 text-right text-xs font-medium text-gray-500">Views</th>
                <th className="px-5 py-2.5 text-right text-xs font-medium text-gray-500">Engagement</th>
                <th className="px-5 py-2.5 text-right text-xs font-medium text-gray-500">GMV</th>
              </tr>
            </thead>
            <tbody>
              {content.map((c, i) => (
                <tr key={c.id} className={`border-b border-[#1f1f1f] hover:bg-[#111111] transition-colors ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#0d0d0d]'}`}>
                  <td className="px-5 py-3 text-white">{c.creator_name}</td>
                  <td className="px-5 py-3 text-gray-500 text-xs truncate max-w-[160px]">{c.product_name || '—'}</td>
                  <td className="px-5 py-3 text-right text-violet-400">
                    {c.views >= 1_000_000 ? `${(c.views/1_000_000).toFixed(1)}M` : `${(c.views/1_000).toFixed(0)}K`}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <span className={c.engagement_rate >= 5 ? 'text-green-400' : c.engagement_rate >= 2 ? 'text-yellow-400' : 'text-gray-400'}>
                      {c.engagement_rate.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right text-yellow-400 font-medium">{formatCurrency(c.gmv_generated)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
