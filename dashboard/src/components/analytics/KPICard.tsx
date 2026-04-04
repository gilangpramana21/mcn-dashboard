import { LucideIcon } from 'lucide-react'

interface KPICardProps {
  title: string
  value: string | number
  icon: LucideIcon
  onClick?: () => void
  isLoading?: boolean
}

export function KPICard({ title, value, icon: Icon, onClick, isLoading }: KPICardProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-[#1f1f1f] bg-[#0d0d0d] p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            <div className="h-4 w-24 animate-pulse rounded bg-gray-800" />
            <div className="h-8 w-32 animate-pulse rounded bg-gray-800" />
          </div>
          <div className="h-10 w-10 animate-pulse rounded-lg bg-gray-800" />
        </div>
      </div>
    )
  }

  return (
    <div 
      className={`rounded-xl border border-[#1f1f1f] bg-[#0d0d0d] p-6 transition-colors ${onClick ? 'cursor-pointer hover:bg-[#1a1a1a]' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm text-gray-400">{title}</p>
          <p className="text-2xl font-semibold text-white">{value}</p>
        </div>
        <div className="rounded-lg bg-violet-600/20 p-2.5">
          <Icon className="h-5 w-5 text-violet-400" />
        </div>
      </div>
    </div>
  )
}
