'use client'
import { useState } from 'react'
import { ShoppingBag, TrendingUp, Users, DollarSign, Search } from 'lucide-react'
import { useAnalytics } from '@/hooks/useAnalytics'
import { ProductTable } from '@/components/analytics/ProductTable'
import { formatCurrency } from '@/lib/formatters'

interface ProductItem {
  id: string
  name: string
  category: string
  price: number
  shop_name: string
  total_videos: number
  total_creators: number
  total_views: number
  total_gmv: number
  avg_conversion_rate: number
  total_buyers: number
  revenue: number
  conversion_rate: number
}

const SORT_OPTIONS = [
  { label: 'GMV', value: 'gmv' },
  { label: 'Buyers', value: 'buyers' },
  { label: 'Creators', value: 'creators' },
  { label: 'Conversion', value: 'conversion' },
]

export default function ProductAnalyticsPage() {
  const [sortBy, setSortBy] = useState('gmv')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [search, setSearch] = useState('')

  const params = { 
    sort_by: sortBy, 
    limit: 100,
    ...(categoryFilter && { category: categoryFilter }),
  }
  const { data: products, loading: isLoading } = useAnalytics<ProductItem[]>('products', params)

  const filtered = (products ?? []).filter(p => 
    !search || p.name.toLowerCase().includes(search.toLowerCase())
  )

  const totalGmv = (products ?? []).reduce((s, p) => s + (p.total_gmv || 0), 0)
  const totalBuyers = (products ?? []).reduce((s, p) => s + (p.total_buyers || 0), 0)
  const validCRProducts = (products ?? []).filter(p => p.avg_conversion_rate != null && !isNaN(p.avg_conversion_rate))
  const avgCR = validCRProducts.length > 0 ? validCRProducts.reduce((s, p) => s + (p.avg_conversion_rate || 0), 0) / validCRProducts.length : 0

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Product Analytics</h1>
        <p className="text-sm text-gray-500 mt-0.5">Produk mana yang paling banyak menghasilkan revenue</p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Produk', value: (products ?? []).length.toString(), color: 'text-white', icon: ShoppingBag, bg: 'bg-violet-600/20 text-violet-400' },
          { label: 'Total GMV', value: formatCurrency(totalGmv), color: 'text-yellow-400', icon: DollarSign, bg: 'bg-yellow-600/20 text-yellow-400' },
          { label: 'Total Buyers', value: totalBuyers.toLocaleString('id-ID'), color: 'text-blue-400', icon: Users, bg: 'bg-blue-600/20 text-blue-400' },
          { label: 'Avg Conversion', value: `${avgCR.toFixed(2)}%`, color: 'text-green-400', icon: TrendingUp, bg: 'bg-green-600/20 text-green-400' },
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
            placeholder="Cari produk..."
            className="rounded-lg border border-[#1f1f1f] bg-[#111111] pl-8 pr-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none w-52" />
        </div>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-gray-300 focus:border-violet-500 focus:outline-none">
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Grid */}
      <ProductTable data={filtered} sortBy={sortBy} onSort={setSortBy} isLoading={isLoading} />
    </div>
  )
}
