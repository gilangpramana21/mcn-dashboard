import { ArrowUpDown, ArrowUp, ArrowDown, MessageCircle } from 'lucide-react'

interface CreatorItem {
  id: string
  name: string
  video_count: number
  total_views: number
  engagement_rate: number
  estimated_revenue: number
  creator_score: number
  creator_role: string
  creator_type: string
  content_categories: string[]
  has_whatsapp: boolean
}

interface CreatorTableProps {
  data: CreatorItem[]
  sortBy: string
  onSort: (field: string) => void
  isLoading?: boolean
  onRowClick?: (id: string) => void
}

const ROLE_COLORS: Record<string, string> = {
  'Superstar': 'bg-yellow-600/20 text-yellow-400 border-yellow-600/30',
  'Rising Star': 'bg-purple-600/20 text-purple-400 border-purple-600/30',
  'Consistent Performer': 'bg-blue-600/20 text-blue-400 border-blue-600/30',
  'Underperformer': 'bg-gray-700/20 text-gray-400 border-gray-700/30',
}

export function CreatorTable({ data, sortBy, onSort, isLoading, onRowClick }: CreatorTableProps) {
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
        <p className="text-gray-500">Belum ada data affiliator</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
            <th onClick={() => onSort('name')} className="px-5 py-3 text-left text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center gap-1.5">Nama <SortIcon field="name" /></div>
            </th>
            <th onClick={() => onSort('video_count')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Videos <SortIcon field="video_count" /></div>
            </th>
            <th onClick={() => onSort('total_views')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Views <SortIcon field="total_views" /></div>
            </th>
            <th onClick={() => onSort('engagement_rate')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Engagement <SortIcon field="engagement_rate" /></div>
            </th>
            <th onClick={() => onSort('estimated_revenue')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Revenue <SortIcon field="estimated_revenue" /></div>
            </th>
            <th onClick={() => onSort('creator_score')} className="px-5 py-3 text-right text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-300">
              <div className="flex items-center justify-end gap-1.5">Score <SortIcon field="creator_score" /></div>
            </th>
            <th className="px-5 py-3 text-center text-xs font-medium text-gray-500">WA</th>
            <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Kategori</th>
            <th className="px-5 py-3 text-center text-xs font-medium text-gray-500">Role</th>
          </tr>
        </thead>
        <tbody>
          {data.map((creator, i) => (
            <tr key={creator.id}
              onClick={() => onRowClick?.(creator.id)}
              className={`border-b border-[#1f1f1f] transition-colors ${onRowClick ? 'cursor-pointer hover:bg-[#1a1a1a]' : 'hover:bg-[#0d0d0d]'} ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#111111]'}`}>
              <td className="px-5 py-3 text-white font-medium">{creator.name}</td>
              <td className="px-5 py-3 text-right text-gray-400">{creator.video_count}</td>
              <td className="px-5 py-3 text-right text-violet-400">
                {creator.total_views >= 1_000_000 ? `${(creator.total_views/1_000_000).toFixed(1)}M` : `${(creator.total_views/1_000).toFixed(0)}K`}
              </td>
              <td className="px-5 py-3 text-right text-blue-400">{(creator.engagement_rate || 0).toFixed(2)}%</td>
              <td className="px-5 py-3 text-right text-yellow-400 font-medium">
                {new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(creator.estimated_revenue)}
              </td>
              <td className="px-5 py-3 text-right text-green-400 font-semibold">{creator.creator_score.toFixed(2)}</td>
              <td className="px-5 py-3 text-center">
                {creator.has_whatsapp
                  ? <MessageCircle className="h-4 w-4 text-green-400 mx-auto" />
                  : <span className="text-gray-700 text-xs">—</span>}
              </td>
              <td className="px-5 py-3">
                <div className="flex flex-wrap gap-1 max-w-[180px]">
                  {(creator.content_categories ?? []).slice(0, 2).map(cat => (
                    <span key={cat} className="inline-flex items-center rounded-full bg-[#1a1a1a] border border-[#2f2f2f] px-2 py-0.5 text-xs text-gray-400 truncate max-w-[85px]">
                      {cat}
                    </span>
                  ))}
                  {(creator.content_categories ?? []).length > 2 && (
                    <span className="text-xs text-gray-600">+{creator.content_categories.length - 2}</span>
                  )}
                </div>
              </td>
              <td className="px-5 py-3 text-center">
                <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[creator.creator_role] ?? 'bg-gray-700/20 text-gray-400 border-gray-700/30'}`}>
                  {creator.creator_role}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
