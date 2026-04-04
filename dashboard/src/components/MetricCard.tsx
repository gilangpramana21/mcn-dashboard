import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value?: string | number
  subtitle?: string
  isLoading?: boolean
  icon?: React.ReactNode
  className?: string
}

export function MetricCard({
  title,
  value,
  subtitle,
  isLoading = false,
  icon,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface p-5 flex flex-col gap-3',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">{title}</span>
        {icon && <span className="text-muted">{icon}</span>}
      </div>

      {isLoading ? (
        <>
          <Skeleton className="h-8 w-32" data-testid="metric-skeleton" />
          {subtitle !== undefined && <Skeleton className="h-4 w-24" />}
        </>
      ) : (
        <>
          <span className="text-2xl font-semibold text-white">{value ?? '—'}</span>
          {subtitle && <span className="text-xs text-muted">{subtitle}</span>}
        </>
      )}
    </div>
  )
}
