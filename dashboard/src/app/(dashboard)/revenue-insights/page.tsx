'use client'
import { useState } from 'react'
import { DollarSign, TrendingUp, Users, ShoppingBag } from 'lucide-react'
import { useAnalytics } from '@/hooks/useAnalytics'
import { RevenueTable } from '@/components/analytics/RevenueTable'
import { formatCurrency } from '@/lib/formatters'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

interface RevenueItem {
  creator_id: string
  creator_name: string
  product_id: string | null
  product_name: string | null
  video_count: number
  revenue: number
  gmv: number
  buyers: number
  conversion_rate: number
}

const SORT_OPTIONS = [
  { label: 'Revenue', value: 'revenue' },
  { label: 'Conversion', value: 'conversion' },
  { label: 'Buyers', value: 'buyers' },
]

export default function RevenueInsightsPage() {
  const [sortBy, setSortBy] = useState('revenue')
  const [creatorFilter, setCreatorFilter] = useState('')
  const [productFilter, setProductFilter] = useState('')

  const params = { 
    sort_by: sortBy, 
    limit: 100,
  }
  const { data, loading: isLoading } = useAnalytics<RevenueItem[]>('revenue', params)

  const filtered = (data ?? []).filter(r =>
    (!creatorFilter || r.creator_id === creatorFilter) &&
    (!productFilter || r.product_id === productFilter)
  )

  const totalRevenue = (data ?? []).reduce((s, r) => s + r.revenue, 0)
  const totalBuyers = (data ?? []).reduce((s, r) => s + r.buyers, 0)
  const avgCR = (data ?? []).length > 0 ? (data ?? []).reduce((s, r) => s + r.conversion_rate, 0) / (data ?? []).length : 0

  const chartData = (data ?? []).slice(0, 10).map(r => ({
    name: r.creator_name.split(' ')[0],
    revenue: r.revenue,
    buyers: r.buyers,
  }))

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Revenue Insights</h1>
        <p className="text-sm text-gray-500 mt-0.5">Siapa yang menghasilkan uang dan dari produk apa</p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-8 w-8 rounded-lg bg-yellow-600/20 flex items-center justify-center">
              <DollarSign className="h-4 w-4 text-yellow-400" />
            </div>
            <p className="text-xs text-gray-500">Total Revenue</p>
          </div>
          <p className="text-2xl font-bold text-yellow-400">{formatCurrency(totalRevenue)}</p>
        </div>
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-8 w-8 rounded-lg bg-blue-600/20 flex items-center justify-center">
              <Users className="h-4 w-4 text-blue-400" />
            </div>
            <p className="text-xs text-gray-500">Total Buyers</p>
          </div>
          <p className="text-2xl font-bold text-blue-400">{totalBuyers.toLocaleString('id-ID')}</p>
        </div>
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-8 w-8 rounded-lg bg-green-600/20 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-green-400" />
            </div>
            <p className="text-xs text-gray-500">Avg Conversion Rate</p>
          </div>
          <p className="text-2xl font-bold text-green-400">{avgCR.toFixed(2)}%</p>
        </div>
      </div>

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Top 10 Kreator by Revenue</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} barSize={28}>
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
        </div>
      )}

      {/* Table */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">Creator × Product × Revenue</h2>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-1.5 text-xs text-gray-300 focus:border-violet-500 focus:outline-none">
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <RevenueTable data={filtered} sortBy={sortBy} onSort={setSortBy} isLoading={isLoading} />
    </div>
  )
}
