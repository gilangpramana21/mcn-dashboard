'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search } from 'lucide-react'
import { useAnalytics } from '@/hooks/useAnalytics'
import { CreatorTable } from '@/components/analytics/CreatorTable'

interface CreatorItem {
  id: string
  name: string
  location: string
  follower_count: number
  engagement_rate: number
  avg_views: number
  estimated_revenue: number
  creator_score: number
  creator_role: string
  creator_type: string
  total_videos: number
  video_count: number
  total_views: number
  total_gmv: number
  content_categories: string[]
  has_whatsapp: boolean
}

const SORT_OPTIONS = [
  { label: 'Creator Score', value: 'score' },
  { label: 'Revenue', value: 'revenue' },
  { label: 'Followers', value: 'followers' },
  { label: 'Engagement', value: 'engagement' },
  { label: 'Views', value: 'views' },
]

export default function CreatorIntelligencePage() {
  const router = useRouter()
  const [sortBy, setSortBy] = useState('score')
  const [typeFilter, setTypeFilter] = useState('')
  const [search, setSearch] = useState('')

  const params = { sort_by: sortBy, limit: 100, ...(typeFilter && { creator_type: typeFilter }) }
  const { data: creators, loading: isLoading } = useAnalytics<CreatorItem[]>('creators', params)

  const filtered = (creators ?? []).filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase())
  )

  const stats = {
    total: creators?.length ?? 0,
    affiliators: creators?.length ?? 0,
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-white">Analitik Affiliator</h1>
        <p className="text-sm text-gray-500 mt-0.5">Analisis performa dan potensi revenue setiap affiliator</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: 'Total Affiliator', value: stats.total, color: 'text-white' },
          { label: 'Affiliator', value: stats.affiliators, color: 'text-green-400' },
        ].map(s => (
          <div key={s.label} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Cari affiliator..."
            className="rounded-lg border border-[#1f1f1f] bg-[#111111] pl-8 pr-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none w-52" />
        </div>
        <div className="flex rounded-lg border border-[#1f1f1f] overflow-hidden">
          {[{ label: 'Semua', value: '' }, { label: 'Affiliator', value: 'affiliator' }].map(r => (
            <button key={r.value} onClick={() => setTypeFilter(r.value)}
              className={`px-3 py-1.5 text-xs transition-colors ${typeFilter === r.value ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'}`}>
              {r.label}
            </button>
          ))}
        </div>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-gray-300 focus:border-violet-500 focus:outline-none">
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Table */}
      <CreatorTable
        data={filtered}
        sortBy={sortBy}
        onSort={setSortBy}
        isLoading={isLoading}
        onRowClick={(id) => router.push(`/affiliates/${id}`)}
      />
    </div>
  )
}
