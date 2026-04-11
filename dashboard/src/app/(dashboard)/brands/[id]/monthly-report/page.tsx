'use client'
import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { ArrowLeft, Plus, Download, Sparkles, Pencil, Check, X } from 'lucide-react'
import Link from 'next/link'

interface MonthlyReport {
  id: string
  brand_name: string
  batch_name: string
  period_start: string
  period_end: string
  total_deal: number
  total_uploaded: number
  total_not_uploaded: number
  total_videos: number
  total_generate_sales: number
  gmv_current: number
  gmv_previous: number
  gmv_video: number
  gmv_live: number
  total_products_sold: number
  total_orders_settled: number
  insight_key_metrics: string
  insight_affiliate: string
  insight_funnel: string
  insight_gmv: string
  insight_product: string
  insight_gap: string
  insight_strategic: string
  next_plan: string
  kesimpulan: string
  top_performers: { username: string; gmv: number; link_acc: string }[]
}

function fmt(n: number) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(n)
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  )
}

function EditableText({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)

  if (!editing) {
    return (
      <div className="group relative">
        <p className="text-sm text-gray-300 whitespace-pre-line bg-[#0a0a0a] rounded-lg p-3 border border-[#1f1f1f] pr-8">{value || '-'}</p>
        <button onClick={() => { setDraft(value); setEditing(true) }}
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-violet-400">
          <Pencil className="h-3.5 w-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <textarea value={draft} onChange={e => setDraft(e.target.value)} rows={5}
        className="w-full rounded-lg border border-violet-500/50 bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:outline-none resize-none" />
      <div className="flex gap-2">
        <button onClick={() => { onSave(draft); setEditing(false) }}
          className="flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-700">
          <Check className="h-3 w-3" /> Simpan
        </button>
        <button onClick={() => setEditing(false)} className="text-xs text-gray-500 hover:text-white">
          <X className="h-3 w-3 inline mr-1" />Batal
        </button>
      </div>
    </div>
  )
}

export default function MonthlyReportPage() {
  const { id: brandId } = useParams<{ id: string }>()
  const router = useRouter()
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [selectedReport, setSelectedReport] = useState<string | null>(null)
  const [previewData, setPreviewData] = useState<any>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)

  const [form, setForm] = useState({
    batch_name: '', period_start: '', period_end: '', gmv_previous: '',
    total_products_sold: '', total_orders_settled: '',
  })

  const { data: reports = [] } = useQuery({
    queryKey: ['monthly-reports', brandId],
    queryFn: () => apiClient.get(`/monthly-reports?brand_id=${brandId}`).then(r => (r as any).data ?? r),
  })

  const { data: report } = useQuery({
    queryKey: ['monthly-report', selectedReport],
    queryFn: () => selectedReport
      ? apiClient.get(`/monthly-reports/${selectedReport}`).then(r => (r as any).data ?? r)
      : null,
    enabled: !!selectedReport,
  })

  const createReport = useMutation({
    mutationFn: (data: any) => apiClient.post('/monthly-reports', data),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ['monthly-reports', brandId] })
      setShowCreate(false)
      setSelectedReport((res as any).data?.id ?? (res as any).id)
    },
  })

  const updateReport = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => apiClient.patch(`/monthly-reports/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['monthly-report', selectedReport] }),
  })

  async function handlePreview() {
    if (!form.period_start || !form.period_end) return
    setLoadingPreview(true)
    try {
      const res = await apiClient.get(
        `/monthly-reports/preview?brand_id=${brandId}&period_start=${form.period_start}&period_end=${form.period_end}&gmv_previous=${form.gmv_previous || 0}`
      )
      setPreviewData((res as any).data ?? res)
    } finally {
      setLoadingPreview(false)
    }
  }

  async function downloadExcel(reportId: string) {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/monthly-reports/${reportId}/export`,
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
    )
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `monthly_report.xlsx`; a.click()
    URL.revokeObjectURL(url)
  }

  const r = report as MonthlyReport | null

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/brands" className="text-gray-500 hover:text-white transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-white">Monthly Report</h1>
          <p className="text-sm text-gray-500">Laporan performa campaign affiliate per periode</p>
        </div>
        <div className="ml-auto flex gap-2">
          {selectedReport && (
            <button onClick={() => downloadExcel(selectedReport)}
              className="flex items-center gap-1.5 rounded-lg border border-[#2f2f2f] px-3 py-2 text-sm text-gray-300 hover:text-white hover:border-green-500 transition-colors">
              <Download className="h-4 w-4 text-green-400" /> Export Excel
            </button>
          )}
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm text-white hover:bg-violet-700">
            <Plus className="h-4 w-4" /> Buat Report
          </button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Sidebar list */}
        <div className="w-56 shrink-0 space-y-2">
          {(reports as any[]).map((rep: any) => (
            <button key={rep.id} onClick={() => setSelectedReport(rep.id)}
              className={`w-full text-left rounded-xl border px-4 py-3 transition-colors ${selectedReport === rep.id ? 'border-violet-500/50 bg-violet-600/10' : 'border-[#1f1f1f] bg-[#111111] hover:border-[#2f2f2f]'}`}>
              <p className="text-sm font-semibold text-white">{rep.batch_name}</p>
              <p className="text-xs text-gray-500">{rep.period_start} – {rep.period_end}</p>
              <p className="text-xs text-violet-400 mt-1">{fmt(rep.gmv_current)}</p>
            </button>
          ))}
          {(reports as any[]).length === 0 && (
            <p className="text-xs text-gray-600 px-2">Belum ada report</p>
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {showCreate && (
            <div className="rounded-xl border border-violet-500/30 bg-[#111111] p-5 space-y-4 mb-6">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-violet-400" />
                <h2 className="text-sm font-semibold text-white">Buat Monthly Report Baru</h2>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Nama Batch</label>
                  <input value={form.batch_name} onChange={e => setForm(p => ({ ...p, batch_name: e.target.value }))}
                    placeholder="Batch 5" className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Periode Mulai</label>
                  <input type="date" value={form.period_start} onChange={e => setForm(p => ({ ...p, period_start: e.target.value }))}
                    className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Periode Selesai</label>
                  <input type="date" value={form.period_end} onChange={e => setForm(p => ({ ...p, period_end: e.target.value }))}
                    className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">GMV Periode Sebelumnya</label>
                  <input type="number" value={form.gmv_previous} onChange={e => setForm(p => ({ ...p, gmv_previous: e.target.value }))}
                    placeholder="0" className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Total Produk Terjual</label>
                  <input type="number" value={form.total_products_sold} onChange={e => setForm(p => ({ ...p, total_products_sold: e.target.value }))}
                    placeholder="0" className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Total Pesanan Settled</label>
                  <input type="number" value={form.total_orders_settled} onChange={e => setForm(p => ({ ...p, total_orders_settled: e.target.value }))}
                    placeholder="0" className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
                </div>
              </div>

              {previewData && (
                <div className="rounded-lg border border-teal-500/30 bg-teal-900/10 p-3">
                  <p className="text-xs font-medium text-teal-400 mb-2">Preview Kalkulasi Otomatis</p>
                  <div className="grid grid-cols-4 gap-2 text-xs text-gray-300">
                    <span>Deal: <b>{previewData.metrics?.total_deal}</b></span>
                    <span>Upload: <b>{previewData.metrics?.total_uploaded}</b></span>
                    <span>Sales: <b>{previewData.metrics?.total_generate_sales}</b></span>
                    <span>GMV: <b>{fmt(previewData.metrics?.gmv_current || 0)}</b></span>
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <button onClick={handlePreview} disabled={!form.period_start || !form.period_end || loadingPreview}
                  className="flex items-center gap-1.5 rounded-lg border border-teal-500/50 px-3 py-2 text-sm text-teal-400 hover:bg-teal-900/20 disabled:opacity-40 transition-colors">
                  <Sparkles className="h-3.5 w-3.5" />
                  {loadingPreview ? 'Menghitung...' : 'Preview AI'}
                </button>
                <button
                  onClick={() => createReport.mutate({
                    brand_id: brandId,
                    ...form,
                    gmv_previous: parseInt(form.gmv_previous) || 0,
                    total_products_sold: parseInt(form.total_products_sold) || 0,
                    total_orders_settled: parseInt(form.total_orders_settled) || 0,
                  })}
                  disabled={!form.batch_name || !form.period_start || !form.period_end || createReport.isPending}
                  className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700 disabled:opacity-40 transition-colors">
                  {createReport.isPending ? 'Menyimpan...' : 'Generate & Simpan'}
                </button>
                <button onClick={() => setShowCreate(false)} className="text-sm text-gray-500 hover:text-white px-3">Batal</button>
              </div>
            </div>
          )}

          {r ? (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-bold text-white">{r.brand_name} — {r.batch_name}</h2>
                <p className="text-sm text-gray-500">{r.period_start} s/d {r.period_end}</p>
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Total Creator Deal" value={r.total_deal} />
                <MetricCard label="Sudah Upload" value={r.total_uploaded} sub={`${r.total_not_uploaded} belum upload`} />
                <MetricCard label="Generate Sales" value={r.total_generate_sales}
                  sub={`${r.total_deal > 0 ? Math.round(r.total_generate_sales / r.total_deal * 100) : 0}% conversion`} />
                <MetricCard label="Total Video" value={r.total_videos} />
                <MetricCard label="GMV Periode Ini" value={fmt(r.gmv_current)} />
                <MetricCard label="GMV Sebelumnya" value={fmt(r.gmv_previous)} />
                <MetricCard label="GMV Video" value={fmt(r.gmv_video)} />
                <MetricCard label="GMV Live" value={fmt(r.gmv_live)} />
              </div>

              {/* Top Performers */}
              {r.top_performers?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">Top Performers</p>
                  <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-[#1f1f1f] bg-[#0a0a0a]">
                          <th className="text-left px-4 py-2 text-xs text-gray-500">#</th>
                          <th className="text-left px-4 py-2 text-xs text-gray-500">Username</th>
                          <th className="text-right px-4 py-2 text-xs text-gray-500">GMV</th>
                        </tr>
                      </thead>
                      <tbody>
                        {r.top_performers.map((tp, i) => (
                          <tr key={i} className="border-b border-[#1f1f1f] last:border-0">
                            <td className="px-4 py-2 text-gray-500 text-xs">{i + 1}</td>
                            <td className="px-4 py-2 text-white">@{tp.username}</td>
                            <td className="px-4 py-2 text-right text-violet-400 font-medium">{fmt(tp.gmv)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Insights — editable */}
              {[
                { key: 'insight_key_metrics', label: 'Insight Key Metrics' },
                { key: 'insight_affiliate', label: 'Analisis Performa Affiliate' },
                { key: 'insight_funnel', label: 'Analisis Funnel Campaign' },
                { key: 'insight_gmv', label: 'Breakdown GMV' },
                { key: 'insight_product', label: 'Produk & Strategi' },
                { key: 'insight_gap', label: 'Gap Operasional' },
                { key: 'insight_strategic', label: 'Insight Strategis' },
                { key: 'next_plan', label: 'Next Plan' },
                { key: 'kesimpulan', label: 'Kesimpulan' },
              ].map(({ key, label }) => (
                <div key={key}>
                  <p className="text-xs font-medium text-gray-500 mb-1.5 uppercase tracking-wider">{label}</p>
                  <EditableText
                    value={(r as any)[key] || ''}
                    onSave={(v) => updateReport.mutate({ id: r.id, data: { [key]: v } })}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-12 text-center">
              <p className="text-gray-500">Pilih report dari daftar atau buat report baru</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
