'use client'

import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import { RankBadge } from './RankBadge'
import { formatFollowerCount, formatEngagementRate } from '@/lib/formatters'
import type { AffiliateCardResponse } from '@/types/api'
import { cn } from '@/lib/utils'

export type SortField = 'follower_count' | 'engagement_rate' | 'gmv_total'
export type SortDirection = 'asc' | 'desc'

interface InfluencerTableProps {
  data: AffiliateCardResponse[]
  isLoading?: boolean
  onRowClick: (id: string) => void
  sortField: SortField
  sortDirection: SortDirection
  onSort: (field: SortField) => void
}

/**
 * Membalik arah sorting jika kolom yang sama diklik, atau set 'desc' untuk kolom baru.
 */
export function toggleSortDirection(
  clickedField: SortField,
  activeField: SortField,
  currentDirection: SortDirection
): SortDirection {
  if (clickedField === activeField) {
    return currentDirection === 'asc' ? 'desc' : 'asc'
  }
  return 'desc'
}

function SortIcon({ field, sortField, sortDirection }: {
  field: SortField
  sortField: SortField
  sortDirection: SortDirection
}) {
  if (field !== sortField) return <ChevronsUpDown className="h-3 w-3 text-gray-600" />
  return sortDirection === 'asc'
    ? <ChevronUp className="h-3 w-3 text-violet-400" />
    : <ChevronDown className="h-3 w-3 text-violet-400" />
}

const SKELETON_ROWS = Array.from({ length: 8 })

export function InfluencerTable({
  data,
  isLoading,
  onRowClick,
  sortField,
  sortDirection,
  onSort,
}: InfluencerTableProps) {
  const sortableHeaders: { field: SortField; label: string }[] = [
    { field: 'follower_count', label: 'Followers' },
    { field: 'engagement_rate', label: 'Engagement' },
    { field: 'gmv_total', label: 'GMV Total' },
  ]

  return (
    <div className="overflow-x-auto rounded-lg border border-[#1f1f1f]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1f1f1f] bg-[#111111]">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-400">Peringkat</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-400">Influencer</th>
            {sortableHeaders.map(({ field, label }) => (
              <th key={field} className="px-4 py-3 text-left">
                <button
                  onClick={() => onSort(field)}
                  className="flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-white transition-colors"
                >
                  {label}
                  <SortIcon field={field} sortField={sortField} sortDirection={sortDirection} />
                </button>
              </th>
            ))}
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-400">Kategori</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-400">Lokasi</th>
          </tr>
        </thead>
        <tbody>
          {isLoading
            ? SKELETON_ROWS.map((_, i) => (
                <tr key={i} className="border-b border-[#1f1f1f]">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 animate-pulse rounded bg-[#1f1f1f]" />
                    </td>
                  ))}
                </tr>
              ))
            : data.map((inf, idx) => (
                <tr
                  key={inf.id}
                  onClick={() => onRowClick(inf.id)}
                  className="cursor-pointer border-b border-[#1f1f1f] transition-colors hover:bg-[#111111]"
                >
                  <td className="px-4 py-3">
                    <RankBadge rank={inf.rank ?? idx + 1} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {inf.photo_url ? (
                        <img
                          src={inf.photo_url}
                          alt={inf.name}
                          className="h-8 w-8 rounded-full object-cover"
                        />
                      ) : (
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-600/20 text-xs font-bold text-violet-400">
                          {inf.name.charAt(0).toUpperCase()}
                        </div>
                      )}
                      <span className="font-medium text-white">{inf.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {formatFollowerCount(inf.follower_count)}
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {formatEngagementRate(inf.engagement_rate)}
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {inf.gmv_total != null
                      ? new Intl.NumberFormat('id-ID', { notation: 'compact' }).format(inf.gmv_total)
                      : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {inf.content_categories.slice(0, 2).map((cat) => (
                        <span
                          key={cat}
                          className="rounded-full bg-[#1f1f1f] px-2 py-0.5 text-xs text-gray-400"
                        >
                          {cat}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{inf.location}</td>
                </tr>
              ))}
        </tbody>
      </table>
    </div>
  )
}
