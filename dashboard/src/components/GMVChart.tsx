'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { formatCurrency, formatDate } from '@/lib/formatters'
import type { GMVDataPoint } from '@/types/api'
import { cn } from '@/lib/utils'

export type ChartMode = 'daily' | 'weekly' | 'monthly'

interface GMVChartProps {
  data: GMVDataPoint[]
  mode: ChartMode
  onModeChange: (mode: ChartMode) => void
  isLoading?: boolean
  className?: string
}

const MODES: { value: ChartMode; label: string }[] = [
  { value: 'daily', label: 'Harian' },
  { value: 'weekly', label: 'Mingguan' },
  { value: 'monthly', label: 'Bulanan' },
]

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 shadow-lg">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-white">
        {formatCurrency(payload[0].value)}
      </p>
    </div>
  )
}

export function GMVChart({ data, mode, onModeChange, isLoading, className }: GMVChartProps) {
  if (isLoading) {
    return (
      <div className={cn('h-64 animate-pulse rounded-lg bg-[#111111]', className)} />
    )
  }

  const formattedData = data.map((d) => ({
    ...d,
    label: formatDate(d.date, mode),
  }))

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex gap-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => onModeChange(m.value)}
            className={cn(
              'rounded px-3 py-1 text-xs font-medium transition-colors',
              mode === m.value
                ? 'bg-violet-600 text-white'
                : 'text-gray-400 hover:text-white'
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={formattedData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="gmvGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" />
          <XAxis
            dataKey="label"
            tick={{ fill: '#888', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => {
              if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
              if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
              return String(v)
            }}
            tick={{ fill: '#888', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="gmv"
            stroke="#7c3aed"
            strokeWidth={2}
            fill="url(#gmvGradient)"
            dot={false}
            activeDot={{ r: 4, fill: '#7c3aed' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
