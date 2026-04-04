import { cn } from '@/lib/utils'

interface RankBadgeProps {
  rank: number
  className?: string
}

/**
 * Mengembalikan kelas warna berdasarkan peringkat:
 * - rank 1–3: emas
 * - rank 4–10: perak
 * - rank > 10: abu-abu
 */
export function getRankBadgeColor(rank: number): string {
  if (rank <= 3) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
  if (rank <= 10) return 'bg-gray-400/20 text-gray-300 border-gray-400/30'
  return 'bg-gray-700/20 text-gray-500 border-gray-700/30'
}

export function RankBadge({ rank, className }: RankBadgeProps) {
  const colorClass = getRankBadgeColor(rank)

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-full border px-2 py-0.5 text-xs font-semibold',
        colorClass,
        className
      )}
    >
      #{rank}
    </span>
  )
}
