'use client'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { AlertTriangle, Info, Upload, Phone, ShoppingBag, TrendingDown, RefreshCw, X } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

interface Alert {
  type: 'warning' | 'info' | 'error'
  category: string
  title: string
  message: string
  count?: number
  brand?: string
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  upload: <Upload className="h-4 w-4 shrink-0" />,
  whatsapp: <Phone className="h-4 w-4 shrink-0" />,
  sku: <ShoppingBag className="h-4 w-4 shrink-0" />,
  gmv: <TrendingDown className="h-4 w-4 shrink-0" />,
}

const TYPE_STYLES: Record<string, string> = {
  warning: 'border-yellow-800/40 bg-yellow-950/30 text-yellow-400',
  info: 'border-blue-800/40 bg-blue-950/30 text-blue-400',
  error: 'border-red-800/40 bg-red-950/30 text-red-400',
}

export function AlertPanel() {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const { data: alerts = [], isLoading, refetch } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => apiClient.get('/alerts').then(r => (r as any).data ?? r),
    refetchInterval: 5 * 60 * 1000, // refresh every 5 min
  })

  const visible = (alerts as Alert[]).filter(a => !dismissed.has(a.title))

  if (isLoading) return null
  if (visible.length === 0) return null

  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1f1f1f]">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-yellow-400" />
          <h2 className="text-sm font-semibold text-white">Alert & Notifikasi</h2>
          <span className="rounded-full bg-yellow-500/20 px-2 py-0.5 text-xs text-yellow-400">
            {visible.length}
          </span>
        </div>
        <button onClick={() => refetch()} className="text-gray-500 hover:text-white transition-colors">
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="divide-y divide-[#1f1f1f]">
        {visible.map((alert) => (
          <div key={alert.title} className={cn(
            'flex items-start gap-3 px-5 py-3 border-l-2',
            alert.type === 'warning' ? 'border-l-yellow-500' :
            alert.type === 'error' ? 'border-l-red-500' : 'border-l-blue-500'
          )}>
            <div className={cn('mt-0.5', TYPE_STYLES[alert.type])}>
              {CATEGORY_ICONS[alert.category] ?? <Info className="h-4 w-4 shrink-0" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white">{alert.title}</p>
              <p className="text-xs text-gray-500 mt-0.5">{alert.message}</p>
            </div>
            <button
              onClick={() => setDismissed(prev => new Set([...prev, alert.title]))}
              className="text-gray-600 hover:text-gray-400 transition-colors shrink-0 mt-0.5"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
