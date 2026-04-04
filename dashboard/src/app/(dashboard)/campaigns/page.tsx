'use client'

import { useState, useMemo } from 'react'
import { useCampaigns, useCampaignReport } from '@/hooks/useCampaigns'
import { MetricCard } from '@/components/MetricCard'
import { formatCurrency, formatDate } from '@/lib/formatters'
import type { CampaignResponse, CampaignReportResponse } from '@/types/api'
import { Megaphone, Play, Pause, CheckCircle, Clock, Search, X, Users, Eye, TrendingUp, DollarSign, Calendar, ChevronRight } from 'lucide-react'

// ─── Status Config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string; icon: any }> = {
  ACTIVE: { label: 'Aktif', color: 'text-green-400', bg: 'bg-green-900/20 border-green-900/30', dot: 'bg-green-400', icon: Play },
  DRAFT: { label: 'Draft', color: 'text-gray-400', bg: 'bg-gray-800/50 border-gray-700/30', dot: 'bg-gray-400', icon: Clock },
  COMPLETED: { label: 'Selesai', color: 'text-violet-400', bg: 'bg-violet-900/20 border-violet-900/30', dot: 'bg-violet-400', icon: CheckCircle },
  PAUSED: { label: 'Dijeda', color: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-900/30', dot: 'bg-yellow-400', icon: Pause },
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_CONFIG[status] ?? STATUS_CONFIG.DRAFT
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${s.color} ${s.bg}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot} ${status === 'ACTIVE' ? 'animate-pulse' : ''}`} />
      {s.label}
    </span>
  )
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function CampaignProgress({ startDate, endDate }: { startDate: string; endDate: string }) {
  const start = new Date(startDate).getTime()
  const end = new Date(endDate).getTime()
  const now = Date.now()
  const progress = Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100))
  const daysLeft = Math.max(0, Math.ceil((end - now) / (1000 * 60 * 60 * 24)))

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>{Math.round(progress)}% selesai</span>
        <span>{daysLeft > 0 ? `${daysLeft} hari lagi` : 'Berakhir'}</span>
      </div>
      <div className="h-1.5 rounded-full bg-[#1a1a1a]">
        <div className="h-1.5 rounded-full bg-violet-500 transition-all" style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="h-16 w-16 rounded-2xl bg-violet-600/10 flex items-center justify-center mb-4">
        <Megaphone className="h-8 w-8 text-violet-400" />
      </div>
      <h3 className="text-base font-semibold text-white">Belum ada kampanye</h3>
      <p className="mt-2 text-sm text-gray-500 max-w-xs">
        Buat kampanye pertama untuk mulai mengelola influencer marketing kamu.
      </p>
    </div>
  )
}

// ─── Campaign Card ────────────────────────────────────────────────────────────

interface CampaignCardProps {
  campaign: CampaignResponse
  isSelected: boolean
  onClick: () => void
}

function CampaignCard({ campaign, isSelected, onClick }: CampaignCardProps) {
  const isActive = campaign.status === 'ACTIVE'
  const statusConf = STATUS_CONFIG[campaign.status] ?? STATUS_CONFIG.DRAFT

  return (
    <button onClick={onClick}
      className={`w-full rounded-xl border text-left transition-all duration-200 overflow-hidden ${
        isSelected
          ? 'border-violet-500/60 bg-violet-500/5 shadow-lg shadow-violet-500/10'
          : 'border-[#1f1f1f] bg-[#111111] hover:border-[#2f2f2f] hover:bg-[#141414]'
      }`}>
      {/* Top accent bar */}
      <div className={`h-0.5 w-full ${isActive ? 'bg-gradient-to-r from-green-500 to-emerald-400' : isSelected ? 'bg-violet-500' : 'bg-[#1f1f1f]'}`} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-white leading-tight">{campaign.name}</p>
            {campaign.description && (
              <p className="mt-1 line-clamp-1 text-xs text-gray-500">{campaign.description}</p>
            )}
          </div>
          <StatusBadge status={campaign.status} />
        </div>

        {/* Date range */}
        <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-3">
          <Calendar className="h-3 w-3" />
          <span>{formatDate(campaign.start_date)}</span>
          <span>→</span>
          <span>{formatDate(campaign.end_date)}</span>
        </div>

        {/* Progress (only for active/paused) */}
        {(campaign.status === 'ACTIVE' || campaign.status === 'PAUSED') && (
          <div className="mb-3">
            <CampaignProgress startDate={campaign.start_date} endDate={campaign.end_date} />
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-[#1a1a1a]">
          <span className="text-xs text-gray-600">
            {campaign.status === 'COMPLETED' ? 'Kampanye selesai' :
             campaign.status === 'DRAFT' ? 'Belum dimulai' :
             campaign.status === 'ACTIVE' ? 'Sedang berjalan' : 'Dijeda'}
          </span>
          <span className={`text-xs font-medium flex items-center gap-1 ${isSelected ? 'text-violet-400' : 'text-gray-600'}`}>
            Lihat laporan <ChevronRight className="h-3 w-3" />
          </span>
        </div>
      </div>
    </button>
  )
}

// ─── Campaign Report Panel ───────────────────────────────────────────────────

interface ReportPanelProps {
  campaignId: string
  campaignName: string
  onClose: () => void
}

function ReportPanel({ campaignId, campaignName, onClose }: ReportPanelProps) {
  const { data: reportRaw, isLoading, isError } = useCampaignReport(campaignId)
  const report: CampaignReportResponse | null = reportRaw
    ? (reportRaw as any).data ?? (reportRaw as unknown as CampaignReportResponse)
    : null

  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f1f1f] bg-[#0d0d0d]">
        <div>
          <p className="text-xs text-gray-500">Laporan Kampanye</p>
          <h2 className="text-sm font-semibold text-white mt-0.5 truncate max-w-[220px]">{campaignName}</h2>
        </div>
        <button onClick={onClose}
          className="rounded-lg border border-[#1f1f1f] p-1.5 text-gray-400 hover:border-[#2f2f2f] hover:text-white transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-5">
        {isLoading && (
          <div className="grid grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 animate-pulse rounded-lg bg-[#1a1a1a]" />
            ))}
          </div>
        )}

        {isError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-center">
            <p className="text-sm text-red-400">Gagal memuat laporan.</p>
          </div>
        )}

        {report && (
          <div className="space-y-4">
            {/* KPI Grid */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Total Influencer', value: report.total_influencers.toString(), icon: Users, color: 'text-blue-400', bg: 'bg-blue-900/20' },
                { label: 'Acceptance Rate', value: `${(report.acceptance_rate * 100).toFixed(1)}%`, icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-900/20' },
                { label: 'Total Views', value: report.total_views >= 1_000_000 ? `${(report.total_views / 1_000_000).toFixed(1)}M` : report.total_views >= 1_000 ? `${(report.total_views / 1_000).toFixed(0)}K` : report.total_views.toString(), icon: Eye, color: 'text-violet-400', bg: 'bg-violet-900/20' },
                { label: 'Total GMV', value: formatCurrency(report.total_gmv), icon: DollarSign, color: 'text-yellow-400', bg: 'bg-yellow-900/20' },
              ].map(m => (
                <div key={m.label} className="rounded-lg border border-[#1f1f1f] bg-[#0d0d0d] p-3">
                  <div className={`h-7 w-7 rounded-lg ${m.bg} flex items-center justify-center mb-2`}>
                    <m.icon className={`h-3.5 w-3.5 ${m.color}`} />
                  </div>
                  <p className={`text-lg font-bold ${m.color}`}>{m.value}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{m.label}</p>
                </div>
              ))}
            </div>

            {/* Cost per conversion */}
            <div className="rounded-lg border border-[#1f1f1f] bg-[#0d0d0d] p-3 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Biaya per Konversi</p>
                <p className="text-sm font-bold text-white mt-0.5">{formatCurrency(report.cost_per_conversion)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Diperbarui</p>
                <p className="text-xs text-gray-400 mt-0.5">{report.generated_at ? formatDate(report.generated_at) : '—'}</p>
              </div>
            </div>

            {/* Acceptance rate bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Tingkat Penerimaan</span>
                <span className="text-green-400 font-medium">{(report.acceptance_rate * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 rounded-full bg-[#1a1a1a]">
                <div className="h-2 rounded-full bg-gradient-to-r from-green-600 to-green-400 transition-all"
                  style={{ width: `${Math.min(100, report.acceptance_rate * 100)}%` }} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function CampaignsPage() {
  const { data: campaigns, isLoading, isError, refetch } = useCampaigns()
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [search, setSearch] = useState('')

  const campaignList: CampaignResponse[] = Array.isArray(campaigns) ? campaigns : []

  const filtered = useMemo(() => campaignList.filter(c => {
    const matchStatus = statusFilter === 'ALL' || c.status === statusFilter
    const matchSearch = c.name.toLowerCase().includes(search.toLowerCase())
    return matchStatus && matchSearch
  }), [campaignList, statusFilter, search])

  const selectedCampaign = campaignList.find((c) => c.id === selectedCampaignId) ?? null

  const stats = useMemo(() => ({
    total: campaignList.length,
    active: campaignList.filter(c => c.status === 'ACTIVE').length,
    draft: campaignList.filter(c => c.status === 'DRAFT').length,
    completed: campaignList.filter(c => c.status === 'COMPLETED').length,
  }), [campaignList])

  function handleSelectCampaign(id: string) {
    setSelectedCampaignId((prev) => (prev === id ? null : id))
  }

  const STATUS_FILTERS = [
    { label: 'Semua', value: 'ALL', icon: Megaphone },
    { label: 'Aktif', value: 'ACTIVE', icon: Play },
    { label: 'Draft', value: 'DRAFT', icon: Clock },
    { label: 'Selesai', value: 'COMPLETED', icon: CheckCircle },
    { label: 'Dijeda', value: 'PAUSED', icon: Pause },
  ]

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Kampanye</h1>
          <p className="mt-1 text-sm text-gray-400">Kelola dan pantau kampanye influencer</p>
        </div>
      </div>

      {/* Stats */}
      {!isLoading && campaignList.length > 0 && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Total', value: stats.total, color: 'text-white' },
            { label: 'Aktif', value: stats.active, color: 'text-green-400' },
            { label: 'Draft', value: stats.draft, color: 'text-gray-400' },
            { label: 'Selesai', value: stats.completed, color: 'text-violet-400' },
          ].map(s => (
            <div key={s.label} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter & Search */}
      {!isLoading && campaignList.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex rounded-lg border border-[#1f1f1f] overflow-hidden">
            {STATUS_FILTERS.map(f => (
              <button key={f.value} onClick={() => setStatusFilter(f.value)}
                className={`px-3 py-1.5 text-xs transition-colors ${statusFilter === f.value ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                {f.label}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-gray-500" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Cari kampanye..."
              className="rounded-lg border border-[#1f1f1f] bg-[#111111] pl-8 pr-3 py-1.5 text-xs text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none w-48" />
          </div>
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center">
          <p className="text-sm text-red-400">Gagal memuat daftar kampanye.</p>
          <button
            onClick={() => refetch()}
            className="mt-3 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Coba Lagi
          </button>
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-xl bg-[#111111]" />
          ))}
        </div>
      )}

      {!isLoading && !isError && campaignList.length === 0 && <EmptyState />}

      {!isLoading && !isError && filtered.length > 0 && (
        <div
          className={`grid gap-6 ${
            selectedCampaignId
              ? 'grid-cols-1 lg:grid-cols-[1fr_380px]'
              : 'grid-cols-1'
          }`}
        >
          {/* Campaign list */}
          <div className="grid auto-rows-min grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((campaign) => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
                isSelected={selectedCampaignId === campaign.id}
                onClick={() => handleSelectCampaign(campaign.id)}
              />
            ))}
          </div>

          {/* Report panel */}
          {selectedCampaignId && selectedCampaign && (
            <div className="lg:sticky lg:top-6 lg:self-start">
              <ReportPanel
                campaignId={selectedCampaignId}
                campaignName={selectedCampaign.name}
                onClose={() => setSelectedCampaignId(null)}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
