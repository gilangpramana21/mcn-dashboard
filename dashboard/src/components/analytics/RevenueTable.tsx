import { ArrowUpDown, ArrowUp, DollarSign } from 'lucide-react'
import { formatCurrency } from '@/lib/formatters'

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

interface RevenueTableProps {
  data: RevenueItem[]
  sortBy: string
  onSort: (field: string) => void
  isLoading?: boolean
}

export function RevenueTable({ data, sortBy, onSort, isLoading }: RevenueTableProps) {
  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-600" />
    return <ArrowUp className="h-3.5 w-3.5 text-violet-400" />
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded-lg bg-[#1a1a1a]" />
        ))}
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-12 text-center">
        <DollarSign className="h-12 w-12 text-gray-700 mx-auto mb-3" />
        <p className="text-gray-500">Belum ada data revenue</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
            <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Kreator</th>
            <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Produk</th>
            <th onClick={() => onSort('videos')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Videos <SortIcon field="videos" /></div>
            </th>
            <th onClick={() => onSort('revenue')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Revenue <SortIcon field="revenue" /></div>
            </th>
            <th onClick={() => onSort('buyers')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Buyers <SortIcon field="buyers" /></div>
            </th>
            <th onClick={() => onSort('conversion')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Conversion <SortIcon field="conversion" /></div>
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((item, i) => (
            <tr key={`${item.creator_id}-${item.product_id}`} className={`border-b border-[#1f1f1f] hover:bg-[#0d0d0d] transition-colors ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#111111]'}`}>
              <td className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-full bg-violet-600/20 flex items-center justify-center text-xs font-bold text-violet-400 shrink-0">
                    {item.creator_name?.charAt(0)?.toUpperCase()}
                  </div>
                  <span className="text-white font-medium">{item.creator_name}</span>
                </div>
              </td>
              <td className="px-5 py-3 text-gray-400 text-xs max-w-[200px] truncate">
                {item.product_name || '—'}
              </td>
              <td className="px-5 py-3 text-right text-gray-400">{item.video_count || 0}</td>
              <td className="px-5 py-3 text-right text-yellow-400 font-semibold">
                {formatCurrency(item.revenue || 0)}
              </td>
              <td className="px-5 py-3 text-right text-blue-400">
                {(item.buyers || 0).toLocaleString('id-ID')}
              </td>
              <td className="px-5 py-3 text-right text-green-400">
                {(item.conversion_rate || 0).toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
