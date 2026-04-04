'use client'

import { useState, useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useReports, calculateROI } from '@/hooks/useReports'
import { RankBadge } from '@/components/RankBadge'
import { formatCurrency, formatFollowerCount } from '@/lib/formatters'
import { apiClient } from '@/lib/api-client'
import type { CampaignReportResponse } from '@/types/api'
import { TrendingUp, Users, Eye, DollarSign } from 'lucide-react'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function extractReports(data: unknown): CampaignReportResponse[] {
  if (!data) return []
  if (Array.isArray(data)) {
    const first = data[0]
    if (first && typeof first === 'object' && 'data' in first) {
      const inner = (first as { data: unknown }).data
      if (Array.isArray(inner)) return inner as CampaignReportResponse[]
      if (inner && typeof inner === 'object') return [inner as CampaignReportResponse]
    }
    return data as CampaignReportResponse[]
  }
  return []
}

// ─── Bar Chart Tooltip ────────────────────────────────────────────────────────

function BarTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 shadow-lg">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-white">{formatCurrency(payload[0].value)}</p>
    </div>
  )
}

// ─── GMV Bar Chart ────────────────────────────────────────────────────────────

interface GMVBarChartProps {
  reports: CampaignReportResponse[]
  isLoading: boolean
}

function GMVBarChart({ reports, isLoading }: GMVBarChartProps) {
  if (isLoading) {
    return <div className="h-64 animate-pulse rounded-lg bg-[#111111]" />
  }

  const chartData = reports.map((r) => ({
    name: r.campaign_name ?? r.campaign_id,
    gmv: r.total_gmv,
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" />
        <XAxis
          dataKey="name"
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
        <Tooltip content={<BarTooltip />} />
        <Bar dataKey="gmv" fill="#7c3aed" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Export Button ────────────────────────────────────────────────────────────

type ExportFormat = 'csv' | 'excel' | 'pdf'

interface ExportButtonProps {
  format: ExportFormat
  startDate: string
  endDate: string
}

function ExportButton({ format, startDate, endDate }: ExportButtonProps) {
  const [loading, setLoading] = useState(false)

  async function handleExport() {
    setLoading(true)
    try {
      const response = await apiClient.post(
        '/api/v1/reports/export',
        { format, start_date: startDate || undefined, end_date: endDate || undefined },
        { responseType: 'blob' }
      )
      const blob = new Blob([response.data as BlobPart])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const ext = format === 'excel' ? 'xlsx' : format
      a.download = `laporan-kampanye.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // error handled by apiClient interceptor
    } finally {
      setLoading(false)
    }
  }

  const labels: Record<ExportFormat, string> = {
    csv: 'CSV',
    excel: 'Excel',
    pdf: 'PDF',
  }

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:border-violet-500/40 hover:text-white disabled:opacity-50"
    >
      {loading ? 'Mengunduh...' : `Ekspor ${labels[format]}`}
    </button>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const { data: reportsRaw, isLoading, isError, refetch } = useReports()

  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const allReports = extractReports(reportsRaw)

  const reports = useMemo(() => {
    if (!startDate && !endDate) return allReports
    return allReports.filter((r) => {
      const date = r.generated_at ? r.generated_at.slice(0, 10) : ''
      if (startDate && date < startDate) return false
      if (endDate && date > endDate) return false
      return true
    })
  }, [allReports, startDate, endDate])

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Laporan</h1>
          <p className="mt-1 text-sm text-gray-400">Perbandingan performa kampanye</p>
        </div>

        {/* Export buttons */}
        <div className="flex flex-wrap gap-2">
          {(['csv', 'excel', 'pdf'] as ExportFormat[]).map((fmt) => (
            <ExportButton key={fmt} format={fmt} startDate={startDate} endDate={endDate} />
          ))}
        </div>
      </div>

      {/* Date range filter */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs text-gray-400">Filter tanggal:</span>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-1.5 text-xs text-gray-300 focus:border-violet-500/60 focus:outline-none"
            aria-label="Tanggal mulai"
          />
          <span className="text-xs text-gray-500">–</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-1.5 text-xs text-gray-300 focus:border-violet-500/60 focus:outline-none"
            aria-label="Tanggal akhir"
          />
        </div>
        {(startDate || endDate) && (
          <button
            onClick={() => { setStartDate(''); setEndDate('') }}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {/* Summary Stats */}
      {!isLoading && !isError && reports.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              label: 'Total Kampanye', icon: TrendingUp, color: 'text-violet-400',
              value: reports.length.toString(),
            },
            {
              label: 'Total Influencer', icon: Users, color: 'text-blue-400',
              value: reports.reduce((s, r) => s + r.total_influencers, 0).toString(),
            },
            {
              label: 'Total Views', icon: Eye, color: 'text-green-400',
              value: (() => {
                const v = reports.reduce((s, r) => s + r.total_views, 0)
                return v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1_000 ? `${(v / 1_000).toFixed(0)}K` : v.toString()
              })(),
            },
            {
              label: 'Total GMV', icon: DollarSign, color: 'text-yellow-400',
              value: formatCurrency(reports.reduce((s, r) => s + r.total_gmv, 0)),
            },
          ].map(s => (
            <div key={s.label} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
              <div className="flex items-center gap-2 mb-2">
                <s.icon className={`h-4 w-4 ${s.color}`} />
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center">
          <p className="text-sm text-red-400">Gagal memuat data laporan.</p>
          <button
            onClick={() => refetch()}
            className="mt-3 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Coba Lagi
          </button>
        </div>
      )}

      {/* GMV Bar Chart */}
      {!isError && (
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <h2 className="mb-4 text-sm font-medium text-white">Perbandingan GMV per Kampanye</h2>
          {isLoading ? (
            <div className="h-64 animate-pulse rounded-lg bg-[#1a1a1a]" />
          ) : reports.length === 0 ? (
            <p className="py-12 text-center text-sm text-gray-500">Tidak ada data untuk ditampilkan.</p>
          ) : (
            <GMVBarChart reports={reports} isLoading={false} />
          )}
        </div>
      )}

      {/* Ranking Table */}
      {!isError && (
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <h2 className="mb-4 text-sm font-medium text-white">Peringkat Kampanye</h2>

          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-lg bg-[#1a1a1a]" />
              ))}
            </div>
          ) : reports.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">Tidak ada data laporan.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#1f1f1f] text-left text-xs text-gray-500">
                    <th className="pb-3 pr-4 font-medium">Peringkat</th>
                    <th className="pb-3 pr-4 font-medium">Nama Kampanye</th>
                    <th className="pb-3 pr-4 font-medium text-right">GMV Total</th>
                    <th className="pb-3 pr-4 font-medium text-right">Acceptance Rate</th>
                    <th className="pb-3 pr-4 font-medium text-right">Total Views</th>
                    <th className="pb-3 pr-4 font-medium text-right">Cost per Conversion</th>
                    <th className="pb-3 font-medium text-right">ROI</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1a1a1a]">
                  {[...reports]
                    .sort((a, b) => b.total_gmv - a.total_gmv)
                    .map((report, idx) => {
                      const roi = calculateROI(
                        report.total_gmv,
                        report.cost_per_conversion,
                        report.total_influencers
                      )
                      const rank = idx + 1
                      return (
                        <tr key={report.campaign_id} className="transition-colors hover:bg-[#161616]">
                          <td className="py-3 pr-4">
                            <RankBadge rank={rank} />
                          </td>
                          <td className="py-3 pr-4 font-medium text-white">
                            {report.campaign_name ?? report.campaign_id}
                          </td>
                          <td className="py-3 pr-4 text-right text-violet-400">
                            {formatCurrency(report.total_gmv)}
                          </td>
                          <td className="py-3 pr-4 text-right text-gray-300">
                            {report.acceptance_rate.toFixed(1)}%
                          </td>
                          <td className="py-3 pr-4 text-right text-gray-300">
                            {formatFollowerCount(report.total_views)}
                          </td>
                          <td className="py-3 pr-4 text-right text-gray-300">
                            {formatCurrency(report.cost_per_conversion)}
                          </td>
                          <td className={`py-3 text-right font-medium ${roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {roi >= 0 ? '+' : ''}{roi.toFixed(1)}%
                          </td>
                        </tr>
                      )
                    })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
