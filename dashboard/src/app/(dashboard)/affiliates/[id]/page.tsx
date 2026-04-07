'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAffiliateDetail } from '@/hooks/useAffiliates'
import { apiClient } from '@/lib/api-client'
import { formatCurrency, formatFollowerCount } from '@/lib/formatters'
import { features } from '@/lib/features'
import {
  ArrowLeft, ExternalLink, Star, ShoppingBag,
  Users, TrendingUp, DollarSign, Play, Radio,
  MessageCircle, Phone, Store, ChevronDown, Check, X,
} from 'lucide-react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
} from 'recharts'

// ─── Types ────────────────────────────────────────────────────────────────────

interface SalesData {
  gmv: number
  products_sold: number
  gpm: number
  gmv_per_buyer_min: number
  gmv_per_buyer_max: number
  gmv_by_channel: { name: string; value: number; color: string }[]
  gmv_by_category: { name: string; value: number; color: string }[]
}

interface CollabData {
  likelihood_pct: number
  avg_commission_rate: number | null
  products: number
  brand_collabs: number
  price_min: number
  price_max: number
}

interface TrendPoint { date: string; value: number }

// ─── Sub-components ───────────────────────────────────────────────────────────

const TABS = ['Penjualan', 'Metrik kolaborasi', 'Video', 'LIVE', 'Pengikut', 'Tren']
const TREND_METRICS = ['GMV', 'Produk terjual', 'Pengikut', 'Tayangan Video', 'Tingkat interaksi']
const TREND_METRIC_MAP: Record<string, string> = {
  'GMV': 'gmv',
  'Produk terjual': 'products_sold',
  'Pengikut': 'followers',
  'Tayangan Video': 'views',
  'Tingkat interaksi': 'engagement',
}

function DonutChart({ data, title }: { data: { name: string; value: number; color: string }[]; title: string }) {
  return (
    <div>
      <p className="text-sm font-medium text-gray-300 mb-3">{title}</p>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width={140} height={140}>
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" strokeWidth={0}>
              {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <Tooltip formatter={(v: any) => `${Number(v).toFixed(2)}%`}
              contentStyle={{ background: '#111', border: '1px solid #1f1f1f', borderRadius: 8, fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="space-y-1.5">
          {data.map((d, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: d.color }} />
              <span className="text-gray-400">{d.name}</span>
              <span className="text-white font-medium ml-auto pl-3">{d.value.toFixed(2)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-[#1f1f1f] ${className ?? ''}`} />
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AffiliateDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { data, isLoading, error } = useAffiliateDetail(params.id)
  const [activeTab, setActiveTab] = useState('Penjualan')
  const [activeTrend, setActiveTrend] = useState('Pengikut')

  const [sales, setSales] = useState<SalesData | null>(null)
  const [collab, setCollab] = useState<CollabData | null>(null)
  const [trendPoints, setTrendPoints] = useState<TrendPoint[]>([])
  const [loadingSales, setLoadingSales] = useState(false)
  const [loadingCollab, setLoadingCollab] = useState(false)
  const [loadingTrend, setLoadingTrend] = useState(false)

  // Chat state
  const [showChatMenu, setShowChatMenu] = useState(false)
  const [chatModal, setChatModal] = useState<'whatsapp' | 'seller_center' | null>(null)
  const [chatMessage, setChatMessage] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const [chatSuccess, setChatSuccess] = useState(false)

  const affiliateId = params.id

  async function handleSendChat() {
    if (!chatMessage.trim() || !chatModal) return
    setChatSending(true)
    try {
      await apiClient.post(`/affiliates/${affiliateId}/contact`, {
        message: chatMessage,
        channel: chatModal,
      })
      setChatSuccess(true)
      setTimeout(() => {
        setChatModal(null)
        setChatMessage('')
        setChatSuccess(false)
      }, 1500)
    } catch {
      // ignore
    } finally {
      setChatSending(false)
    }
  }

  // Load sales data when tab = Penjualan
  useEffect(() => {
    if (activeTab !== 'Penjualan' || sales) return
    setLoadingSales(true)
    apiClient.get(`/analytics/affiliate/${affiliateId}/sales`)
      .then(r => setSales(r.data))
      .catch(() => setSales(null))
      .finally(() => setLoadingSales(false))
  }, [activeTab, affiliateId])

  // Load collab data when tab = Metrik kolaborasi
  useEffect(() => {
    if (activeTab !== 'Metrik kolaborasi' || collab) return
    setLoadingCollab(true)
    apiClient.get(`/analytics/affiliate/${affiliateId}/collab`)
      .then(r => setCollab(r.data))
      .catch(() => setCollab(null))
      .finally(() => setLoadingCollab(false))
  }, [activeTab, affiliateId])

  // Load trend data when tab = Tren or metric changes
  useEffect(() => {
    if (activeTab !== 'Tren') return
    const metric = TREND_METRIC_MAP[activeTrend] ?? 'followers'
    setLoadingTrend(true)
    apiClient.get(`/analytics/affiliate/${affiliateId}/trend`, { params: { metric } })
      .then(r => setTrendPoints(r.data.points ?? []))
      .catch(() => setTrendPoints([]))
      .finally(() => setLoadingTrend(false))
  }, [activeTab, activeTrend, affiliateId])

  const is404 = (error as any)?.response?.status === 404

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    )
  }

  if (is404 || (!isLoading && error)) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6">
        <p className="text-xl font-bold text-white">Affiliator tidak ditemukan</p>
        <p className="text-sm text-gray-500">{(error as any)?.message || 'Terjadi kesalahan'}</p>
        <button onClick={() => router.back()} className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700">
          ← Kembali
        </button>
      </div>
    )
  }

  const aff = data?.data
  if (!isLoading && !aff) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6">
        <p className="text-xl font-bold text-white">Data tidak tersedia</p>
        <button onClick={() => router.back()} className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700">
          ← Kembali
        </button>
      </div>
    )
  }

  if (!aff) return null

  const dateRange = `${new Date(Date.now() - 30 * 86400000).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })} – ${new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })} (GMT+7)`

  return (
    <>
    <div className="min-h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="border-b border-[#1f1f1f] bg-[#0d0d0d] px-6 py-3">
        <button onClick={() => router.back()} className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors">
          <ArrowLeft className="h-4 w-4" /> Detail kreator
        </button>
      </div>

      {/* Profile */}
      <div className="border-b border-[#1f1f1f] bg-[#0d0d0d] px-6 py-5">
        <div className="flex items-start gap-5">
          <div className="h-16 w-16 rounded-full bg-gradient-to-br from-violet-500 to-teal-500 flex items-center justify-center text-2xl font-bold text-white shrink-0">
            {aff.name?.charAt(0)?.toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-lg font-bold text-white">{aff.name}</h1>
              <span className="flex items-center gap-1 rounded-full bg-yellow-500/20 border border-yellow-500/30 px-2 py-0.5 text-xs text-yellow-400">
                <Star className="h-3 w-3" /> Lv. 2
              </span>
            </div>
            {aff.location && <p className="text-sm text-gray-500 mt-0.5">{aff.location}</p>}
            {aff.tiktok_username && (
              <a
                href={aff.tiktok_profile_url || `https://www.tiktok.com/@${aff.tiktok_username.replace('@','')}`}
                target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 mt-1 text-xs text-gray-400 hover:text-white transition-colors"
              >
                <span className="rounded-full bg-[#1a1a1a] border border-[#2f2f2f] px-2 py-0.5 text-[10px] font-medium text-gray-300">
                  TikTok
                </span>
                {aff.tiktok_username}
              </a>
            )}
            {aff.tiktok_creator_id && (
              <div className="inline-flex items-center gap-1.5 mt-1">
                <span className="rounded-full bg-[#1a1a1a] border border-teal-800/50 px-2 py-0.5 text-[10px] font-medium text-teal-400">
                  TikTok Shop ID
                </span>
                <span className="text-xs text-gray-400 font-mono">{aff.tiktok_creator_id}</span>
              </div>
            )}
            <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Rating</span>
                <p className="text-white font-medium mt-0.5">Belum ada rating</p>
              </div>
              <div>
                <span className="text-gray-500">Kategori</span>
                <p className="text-white font-medium mt-0.5 truncate">
                  {aff.content_categories?.slice(0, 2).join(', ') || '—'}
                  {(aff.content_categories?.length ?? 0) > 2 && <span className="text-gray-500"> +{aff.content_categories.length - 2}</span>}
                </p>
              </div>
              <div>
                <span className="text-gray-500">Pengikut</span>
                <p className="text-white font-medium mt-0.5">{formatFollowerCount(aff.follower_count)}</p>
              </div>
            </div>
          </div>
          {aff.bio && (
            <div className="hidden lg:block max-w-xs text-xs text-gray-400 leading-relaxed border-l border-[#1f1f1f] pl-5">
              {aff.bio.split('\n').map((line, i) => <p key={i}>{line}</p>)}
            </div>
          )}
          <div className="flex items-center gap-2 shrink-0">
            {/* Chat dropdown - hanya tampil jika showWhatsApp atau untuk Seller Center */}
            <div className="relative">
              <button
                onClick={() => setShowChatMenu(v => !v)}
                className="flex items-center gap-1.5 rounded-lg border border-[#2f2f2f] px-3 py-2 text-sm text-gray-300 hover:text-white hover:border-violet-500 transition-colors"
              >
                <MessageCircle className="h-4 w-4" />
                Chat
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
              {showChatMenu && (
                <div className="absolute right-0 top-full mt-1 w-52 rounded-xl border border-[#1f1f1f] bg-[#111111] shadow-xl z-20 overflow-hidden">
                  {features.showWhatsApp && (
                    aff.phone_number ? (
                      <button
                        onClick={() => { setChatModal('whatsapp'); setShowChatMenu(false) }}
                        className="flex w-full items-center gap-3 px-4 py-3 text-sm text-gray-300 hover:bg-[#1a1a1a] hover:text-white transition-colors"
                      >
                        <Phone className="h-4 w-4 text-green-400" />
                        <div className="text-left">
                          <p className="font-medium">WhatsApp</p>
                          <p className="text-xs text-gray-500">{aff.phone_number}</p>
                        </div>
                      </button>
                    ) : (
                      <div className="flex items-center gap-3 px-4 py-3 text-sm text-gray-600 cursor-not-allowed">
                        <Phone className="h-4 w-4" />
                        <div className="text-left">
                          <p>WhatsApp</p>
                          <p className="text-xs">Nomor belum tersedia</p>
                        </div>
                      </div>
                    )
                  )}
                  {features.showWhatsApp && <div className="border-t border-[#1f1f1f]" />}
                  <button
                    onClick={() => { setChatModal('seller_center'); setShowChatMenu(false) }}
                    className="flex w-full items-center gap-3 px-4 py-3 text-sm text-gray-300 hover:bg-[#1a1a1a] hover:text-white transition-colors"
                  >
                    <Store className="h-4 w-4 text-violet-400" />
                    <div className="text-left">
                      <p className="font-medium">Seller Center Chat</p>
                      <p className="text-xs text-gray-500">Via TikTok Seller Center</p>
                    </div>
                  </button>
                </div>
              )}
            </div>

            {aff.tiktok_profile_url && (
              <a href={aff.tiktok_profile_url} target="_blank" rel="noopener noreferrer"
                className="rounded-lg border border-[#2f2f2f] p-2 text-gray-400 hover:text-white hover:border-violet-500 transition-colors">
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>

          {/* Overlay to close menu */}
          {showChatMenu && (
            <div className="fixed inset-0 z-10" onClick={() => setShowChatMenu(false)} />
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-[#1f1f1f] bg-[#0d0d0d] px-6">
        <div className="flex gap-0">
          {TABS.map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab ? 'border-teal-500 text-teal-400' : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}>
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">

        {/* ── PENJUALAN ── */}
        {activeTab === 'Penjualan' && (
          <>
            <div>
              <h2 className="text-base font-semibold text-white">Penjualan</h2>
              <p className="text-xs text-gray-500 mt-0.5">{dateRange}</p>
            </div>
            {loadingSales ? (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
              </div>
            ) : sales ? (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    { label: 'GMV', value: `Rp${(sales.gmv / 1_000_000).toFixed(0)}JT+`, icon: DollarSign },
                    { label: 'Produk terjual', value: sales.products_sold.toLocaleString('id-ID'), icon: ShoppingBag },
                    { label: 'GPM', value: formatCurrency(sales.gpm), icon: TrendingUp },
                    { label: 'GMV per pembeli', value: `${formatCurrency(sales.gmv_per_buyer_min)}–${formatCurrency(sales.gmv_per_buyer_max)}`, icon: Users },
                  ].map(kpi => (
                    <div key={kpi.label} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
                      <p className="text-xs text-gray-500 flex items-center gap-1">
                        <kpi.icon className="h-3.5 w-3.5" /> {kpi.label}
                      </p>
                      <p className="text-xl font-bold text-white mt-2">{kpi.value}</p>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
                    <DonutChart data={sales.gmv_by_channel} title="GMV per saluran penjualan" />
                  </div>
                  <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
                    <DonutChart data={sales.gmv_by_category} title="GMV berdasarkan kategori produk" />
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-8 text-center text-gray-500">
                Belum ada data penjualan
              </div>
            )}
          </>
        )}

        {/* ── METRIK KOLABORASI ── */}
        {activeTab === 'Metrik kolaborasi' && (
          <>
            <h2 className="text-base font-semibold text-white">Metrik kolaborasi</h2>
            {loadingCollab ? (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
              </div>
            ) : collab ? (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    { label: 'Perkiraan kemungkinan menerima', value: `${collab.likelihood_pct}%`, sub: null },
                    { label: 'Rata-rata persentase komisi', value: collab.avg_commission_rate != null ? `${collab.avg_commission_rate}%` : '—', sub: null },
                    { label: 'Produk', value: collab.products.toString(), sub: null },
                    { label: 'Kolaborasi merek', value: collab.brand_collabs.toString(), sub: 'Lihat merek teratas' },
                  ].map(m => (
                    <div key={m.label} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
                      <p className="text-xs text-gray-500">{m.label}</p>
                      <p className="text-2xl font-bold text-white mt-2">{m.value}</p>
                      {m.sub && <p className="text-xs text-teal-400 mt-1 cursor-pointer hover:underline">{m.sub}</p>}
                    </div>
                  ))}
                </div>
                {(collab.price_min > 0 || collab.price_max > 0) && (
                  <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
                    <p className="text-sm font-medium text-gray-300 mb-2">Harga produk</p>
                    <p className="text-2xl font-bold text-white">
                      {formatCurrency(collab.price_min)} – {formatCurrency(collab.price_max)}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Rentang harga produk yang biasa dipromosikan</p>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-8 text-center text-gray-500">
                Belum ada data kolaborasi
              </div>
            )}
          </>
        )}

        {/* ── VIDEO ── */}
        {activeTab === 'Video' && (
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-8 text-center">
            <Play className="h-12 w-12 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400">Data video belum tersedia</p>
          </div>
        )}

        {/* ── LIVE ── */}
        {activeTab === 'LIVE' && (
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-8 text-center">
            <Radio className="h-12 w-12 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400">Data LIVE belum tersedia</p>
          </div>
        )}

        {/* ── PENGIKUT ── */}
        {activeTab === 'Pengikut' && (
          <>
            <h2 className="text-base font-semibold text-white">Pengikut</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
                <DonutChart
                  data={[
                    { name: 'Perempuan', value: 79.99, color: '#f59e0b' },
                    { name: 'Laki-laki', value: 20.01, color: '#14b8a6' },
                  ]}
                  title="Jenis kelamin"
                />
              </div>
              <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
                <DonutChart
                  data={[
                    { name: '18–24', value: 44.5, color: '#14b8a6' },
                    { name: '25–34', value: 44.7, color: '#f59e0b' },
                    { name: '35–44', value: 6.9, color: '#3b82f6' },
                    { name: '45–54', value: 1.9, color: '#8b5cf6' },
                    { name: '55+', value: 2.0, color: '#ec4899' },
                  ]}
                  title="Usia"
                />
              </div>
            </div>
            <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
              <p className="text-sm font-medium text-gray-300 mb-4">5 lokasi teratas</p>
              <div className="space-y-3">
                {[
                  { name: 'WEST JAVA', value: 95 },
                  { name: 'EAST JAVA', value: 88 },
                  { name: 'CENTRAL JAVA', value: 82 },
                  { name: 'JAKARTA', value: 55 },
                  { name: 'BANTEN', value: 30 },
                ].map(loc => (
                  <div key={loc.name} className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-28 shrink-0">{loc.name}</span>
                    <div className="flex-1 h-5 rounded bg-[#1a1a1a] overflow-hidden">
                      <div className="h-5 rounded bg-teal-500 transition-all" style={{ width: `${loc.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ── TREN ── */}
        {activeTab === 'Tren' && (
          <>
            <div>
              <h2 className="text-base font-semibold text-white">Tren</h2>
              <p className="text-xs text-gray-500 mt-0.5">{dateRange}</p>
            </div>
            <div className="flex gap-0 border-b border-[#1f1f1f]">
              {TREND_METRICS.map(m => (
                <button key={m} onClick={() => setActiveTrend(m)}
                  className={`px-4 py-2.5 text-sm border-b-2 transition-colors ${
                    activeTrend === m ? 'border-teal-500 text-teal-400' : 'border-transparent text-gray-500 hover:text-gray-300'
                  }`}>
                  {m}
                </button>
              ))}
            </div>
            <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-2.5 w-2.5 rounded-full bg-teal-500" />
                <span className="text-xs text-gray-400">{activeTrend}</span>
              </div>
              {loadingTrend ? (
                <Skeleton className="h-52 rounded-lg" />
              ) : trendPoints.length === 0 ? (
                <div className="h-52 flex items-center justify-center text-gray-600 text-sm">Belum ada data</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={trendPoints}>
                    <defs>
                      <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false}
                      interval={Math.floor(trendPoints.length / 6)} />
                    <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false}
                      tickFormatter={v => v >= 1_000_000 ? `${(v/1_000_000).toFixed(1)}M` : v >= 1_000 ? `${(v/1_000).toFixed(0)}K` : v} />
                    <Tooltip contentStyle={{ background: '#111', border: '1px solid #1f1f1f', borderRadius: 8, fontSize: 11 }}
                      labelStyle={{ color: '#9ca3af' }}
                      formatter={(v: any) => [
                        activeTrend === 'GMV' ? formatCurrency(v) : Number(v).toLocaleString('id-ID'),
                        activeTrend
                      ]} />
                    <Area type="monotone" dataKey="value" stroke="#14b8a6" strokeWidth={2} fill="url(#trendGrad)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </>
        )}
      </div>
    </div>

    {/* Chat Modal */}
    {chatModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
        <div className="w-full max-w-sm rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 shadow-2xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {chatModal === 'whatsapp'
                ? <Phone className="h-4 w-4 text-green-400" />
                : <Store className="h-4 w-4 text-violet-400" />}
              <p className="text-sm font-semibold text-white">
                {chatModal === 'whatsapp' ? 'Kirim via WhatsApp' : 'Kirim via Seller Center'}
              </p>
            </div>
            <button onClick={() => { setChatModal(null); setChatMessage('') }}
              className="text-gray-500 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="text-xs text-gray-400 mb-3">
            Kepada: <span className="text-white font-medium">{aff?.name}</span>
            {features.showWhatsApp && chatModal === 'whatsapp' && aff?.phone_number && (
              <span className="text-gray-500"> · {aff.phone_number}</span>
            )}
          </p>
          {chatSuccess ? (
            <div className="flex items-center gap-2 text-green-400 py-3">
              <Check className="h-4 w-4" />
              <span className="text-sm">Pesan berhasil dikirim!</span>
            </div>
          ) : (
            <>
              <textarea
                value={chatMessage}
                onChange={e => setChatMessage(e.target.value)}
                placeholder="Tulis pesan..."
                rows={4}
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none resize-none mb-3"
              />
              <button
                onClick={handleSendChat}
                disabled={chatSending || !chatMessage.trim()}
                className="w-full rounded-lg bg-violet-600 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40 transition-colors"
              >
                {chatSending ? 'Mengirim...' : 'Kirim Pesan'}
              </button>
            </>
          )}
        </div>
      </div>
    )}
  </>
  )
}
