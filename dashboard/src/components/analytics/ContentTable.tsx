import { ArrowUpDown, ArrowUp, Play } from 'lucide-react'
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
  velocity: number
  posted_at: string
}

interface ContentTableProps {
  data: ContentItem[]
  sortBy: string
  onSort: (field: string) => void
  isLoading?: boolean
}

export function ContentTable({ data, sortBy, onSort, isLoading }: ContentTableProps) {
  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-600" />
    return <ArrowUp className="h-3.5 w-3.5 text-violet-400" />
  }

  function getEngagementColor(rate: number): string {
    if (rate >= 5) return 'text-green-400'
    if (rate >= 2) return 'text-yellow-400'
    return 'text-gray-400'
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
        <Play className="h-12 w-12 text-gray-700 mx-auto mb-3" />
        <p className="text-gray-500">Belum ada data konten</p>
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
            <th onClick={() => onSort('engagement')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Engagement <SortIcon field="engagement" /></div>
            </th>
            <th onClick={() => onSort('gmv')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">GMV <SortIcon field="gmv" /></div>
            </th>
            <th onClick={() => onSort('conversion')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Conversion <SortIcon field="conversion" /></div>
            </th>
            <th className="px-5 py-3 text-right text-xs font-medium text-gray-500">Posted</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item, i) => (
            <tr key={item.id} className={`border-b border-[#1f1f1f] hover:bg-[#0d0d0d] transition-colors ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#111111]'}`}>
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
              <td className="px-5 py-3 text-right">
                <span className={getEngagementColor(item.engagement_rate || 0)}>
                  {(item.engagement_rate || 0).toFixed(1)}%
                </span>
              </td>
              <td className="px-5 py-3 text-right text-yellow-400 font-medium">
                {formatCurrency(item.gmv_generated || 0)}
              </td>
              <td className="px-5 py-3 text-right text-blue-400">
                {(item.conversion_rate || 0).toFixed(2)}%
              </td>
              <td className="px-5 py-3 text-right text-gray-500 text-xs">
                {new Date(item.posted_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
