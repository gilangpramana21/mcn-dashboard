import { cn } from '@/lib/utils'
import type { CampaignStatus } from '@/types/api'

interface StatusIndicatorProps {
  status: CampaignStatus
  className?: string
}

const STATUS_LABELS: Record<CampaignStatus, string> = {
  ACTIVE: 'Aktif',
  DRAFT: 'Draft',
  PAUSED: 'Dijeda',
  STOPPED: 'Dihentikan',
  COMPLETED: 'Selesai',
}

/**
 * Mengembalikan kelas warna berdasarkan status kampanye:
 * - ACTIVE: hijau
 * - DRAFT: abu-abu
 * - PAUSED: kuning
 * - STOPPED: merah
 * - COMPLETED: biru
 */
export function getStatusColor(status: CampaignStatus): string {
  const colorMap: Record<CampaignStatus, string> = {
    ACTIVE: 'bg-green-500/20 text-green-400 border-green-500/30',
    DRAFT: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    PAUSED: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    STOPPED: 'bg-red-500/20 text-red-400 border-red-500/30',
    COMPLETED: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }
  return colorMap[status]
}

export function StatusIndicator({ status, className }: StatusIndicatorProps) {
  const colorClass = getStatusColor(status)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        colorClass,
        className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATUS_LABELS[status]}
    </span>
  )
}
