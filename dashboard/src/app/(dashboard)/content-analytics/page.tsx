'use client'
import { useState } from 'react'
import { TrendingUp, DollarSign, Search, Users } from 'lucide-react'
import { useAnalytics } from '@/hooks/useAnalytics'
import { ContentTable } from '@/components/analytics/ContentTable'
import { formatCurrency } from '@/lib/formatters'

interface ContentItem {
  id: string
  tiktok_video_id: string
  creator_name: string
  product_name: string | null
  title: string
  views: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number
  gmv_generated: number
  conversion_rate: number
  buyers?: number
  velocity: number
  posted_at: string
}

const SORT_OPTIONS = [
  { label: 'GMV', value: 'gmv' },
  { label: 'Engagement', value: 'engagement' },
  { label: 'Views', value: 'views' },
  { label: 'Velocity', value: 'velocity' },
]

export default function ContentAnalyticsPage() {
  const [sortBy, setSortBy] = useState('gmv')
  const [search, setSearch] = useState('')

  const { data: content, loading: isLoading } = useAnalytics<ContentItem[]>('content', { sort_by: sortBy, limit: 50 })

  const filtered = (content ?? []).filter(c =>
    !search || c.creator_name.toLowerCase().includes(search.toLowerCase()) ||
    (c.product_name && c.product_name.toLowerCase().includes(search.toLowerCase()))
  )

  const totalGmv = (content ?? []).reduce((s, c) => s + c.gmv_generated, 0)
  const totalBuyers = (content ?? []).reduce((s, c) => s + (c.buyers ?? 0), 0)
  const avgER = (content ?? []).length > 0
    ? (content ?? []).reduce((s, c) => s + c.engagement_rate, 0) / (content ?? []).length
    : 0
  const avgCR = (content ?? []).length > 0
    ? (content ?? []).reduce((s, c) => s + c.conversion_rate, 0) / (content ?? []).length
    : 0

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Content Analytics</h1>
        <p className="text-sm text-gray-500 mt-0.5">Performa konten video per affiliator</p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total GMV', value: formatCurrency(totalGmv), color: 'text-yellow-400', icon: DollarSign, bg: 'bg-yellow-600/20 text-yellow-400' },
          { label: 'Avg Engagement', value: `${avgER.toFixed(1)}%`, color: 'text-green-400', icon: TrendingUp, bg: 'bg-green-600/20 text-green-400' },
          { label: 'Total Buyers', value: totalBuyers.toLocaleString('id-ID'), color: 'text-blue-400', icon: Users, bg: 'bg-blue-600/20 text-blue-400' },
        ].map(s => (
          <div key={s.label} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <div className={`h-8 w-8 rounded-lg ${s.bg} flex items-center justify-center mb-3`}>
              <s.icon className="h-4 w-4" />
            </div>
            <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Cari affiliator atau produk..."
            className="rounded-lg border border-[#1f1f1f] bg-[#111111] pl-8 pr-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none w-60" />
        </div>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-gray-300 focus:border-violet-500 focus:outline-none">
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Table */}
      <ContentTable data={filtered} sortBy={sortBy} onSort={setSortBy} isLoading={isLoading} />
    </div>
  )
}
