'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search, SlidersHorizontal, X, ChevronDown, ChevronUp, RotateCcw, MessageCircle, Phone, Upload, Check } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { features } from '@/lib/features'

// ─── Filter Data ─────────────────────────────────────────────────────────────

const CREATOR_CATEGORIES = [
  // Beauty & Personal Care
  'Kecantikan', 'Perawatan Kulit', 'Perawatan Rambut', 'Parfum & Wewangian',
  // Fashion
  'Fashion Wanita', 'Fashion Pria', 'Fashion Anak', 'Tas & Dompet', 'Sepatu', 'Aksesoris',
  // Food & Beverage
  'Makanan & Minuman', 'Makanan Ringan', 'Minuman', 'Suplemen & Vitamin',
  // Home & Living
  'Rumah & Dekorasi', 'Peralatan Dapur', 'Perlengkapan Tidur',
  // Electronics
  'Elektronik', 'Handphone & Aksesoris', 'Komputer & Laptop', 'Kamera',
  // Mother & Baby
  'Ibu & Bayi', 'Mainan Anak',
  // Sports & Outdoor
  'Olahraga & Outdoor', 'Alat Fitness',
  // Automotive
  'Otomotif & Aksesoris',
  // Pets
  'Hewan Peliharaan',
  // Entertainment
  'Gaming', 'Buku & Alat Tulis',
]

const DELIVERY_CATEGORIES = [
  'Pengiriman Gratis', 'COD (Bayar di Tempat)', 'Same Day Delivery',
  'Next Day Delivery', 'Pengiriman Reguler',
]

const SALES_METHODS = [
  'Live Shopping', 'Video Pendek (Short Video)', 'Showcase (Etalase)',
  'Affiliate Link', 'Kolaborasi Produk',
]

const FOLLOWER_RANGES = [
  { label: 'Semua', min: '', max: '' },
  { label: 'Nano (1K–10K)', min: '1000', max: '10000' },
  { label: 'Micro (10K–100K)', min: '10000', max: '100000' },
  { label: 'Mid (100K–500K)', min: '100000', max: '500000' },
  { label: 'Macro (500K–1M)', min: '500000', max: '1000000' },
  { label: 'Mega (1M+)', min: '1000000', max: '' },
]

const ENGAGEMENT_RANGES = [
  { label: 'Semua', value: '' },
  { label: '1%+', value: '0.01' },
  { label: '3%+', value: '0.03' },
  { label: '5%+', value: '0.05' },
  { label: '10%+', value: '0.10' },
]

const SORT_OPTIONS = [
  { label: 'Followers Terbanyak', value: 'followers_desc' },
  { label: 'Engagement Tertinggi', value: 'engagement_desc' },
  { label: 'Relevansi', value: 'relevance_desc' },
  { label: 'Terbaru', value: 'newest' },
]

const LOCATIONS = [
  'Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Semarang',
  'Makassar', 'Palembang', 'Tangerang', 'Depok', 'Bekasi',
  'Yogyakarta', 'Bali', 'Bogor', 'Malang', 'Batam',
]

// ─── Sub-components ───────────────────────────────────────────────────────────

function FilterSection({ title, children, defaultOpen = false }: {
  title: string; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-[#1f1f1f] last:border-0">
      <button onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-3 text-sm font-medium text-gray-300 hover:text-white">
        {title}
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && <div className="pb-4">{children}</div>}
    </div>
  )
}

function TagGroup({ items, selected, onToggle }: {
  items: string[]; selected: string[]; onToggle: (v: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map(item => (
        <button key={item} onClick={() => onToggle(item)}
          className={`rounded-full px-3 py-1 text-xs transition-colors ${
            selected.includes(item)
              ? 'bg-violet-600 text-white'
              : 'border border-[#2f2f2f] text-gray-400 hover:text-white'
          }`}>
          {item}
        </button>
      ))}
    </div>
  )
}

function RadioGroup({ items, selected, onSelect }: {
  items: { label: string; value: string }[]; selected: string; onSelect: (v: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map(item => (
        <button key={item.value} onClick={() => onSelect(item.value)}
          className={`rounded-full px-3 py-1 text-xs transition-colors ${
            selected === item.value
              ? 'bg-violet-600 text-white'
              : 'border border-[#2f2f2f] text-gray-400 hover:text-white'
          }`}>
          {item.label}
        </button>
      ))}
    </div>
  )
}

function formatFollowers(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AffiliatesPage() {
  const router = useRouter()
  const [searchName, setSearchName] = useState('')
  const [followerRange, setFollowerRange] = useState({ min: '', max: '' })
  const [engagementMin, setEngagementMin] = useState('')
  const [creatorCategories, setCreatorCategories] = useState<string[]>([])
  const [deliveryCategories, setDeliveryCategories] = useState<string[]>([])
  const [salesMethods, setSalesMethods] = useState<string[]>([])
  const [hasWhatsapp, setHasWhatsapp] = useState<string>('')
  const [sortBy, setSortBy] = useState('followers_desc')
  const [locations, setLocations] = useState<string[]>([])

  const [affiliates, setAffiliates] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [page, setPage] = useState(1)

  // Update WA modal
  const [waModal, setWaModal] = useState<{ id: string; name: string } | null>(null)
  const [waInput, setWaInput] = useState('')
  const [waSaving, setWaSaving] = useState(false)
  const [waSuccess, setWaSuccess] = useState(false)

  function toggleTag(list: string[], setList: (v: string[]) => void, val: string) {
    setList(list.includes(val) ? list.filter(x => x !== val) : [...list, val])
  }

  const activeCount = [
    searchName, followerRange.min || followerRange.max, engagementMin, hasWhatsapp,
    ...creatorCategories, ...deliveryCategories, ...salesMethods, ...locations,
  ].filter(Boolean).length

  async function handleSearch(p = 1) {
    setIsLoading(true)
    setSearched(true)
    setPage(p)
    try {
      const params = new URLSearchParams({ page: String(p), page_size: '100', sort_by: sortBy })
      if (searchName) params.set('name', searchName)
      if (followerRange.min) params.set('min_followers', followerRange.min)
      if (followerRange.max) params.set('max_followers', followerRange.max)
      if (engagementMin) params.set('min_engagement_rate', engagementMin)
      if (hasWhatsapp === 'yes') params.set('has_whatsapp', 'true')
      if (hasWhatsapp === 'no') params.set('has_whatsapp', 'false')
      creatorCategories.forEach(c => params.append('categories', c))
      locations.forEach(l => params.append('locations', l))
      if (deliveryCategories.length) params.set('delivery_categories', deliveryCategories.join(','))
      if (salesMethods.length) params.set('sales_methods', salesMethods.join(','))

      const { data } = await apiClient.get(`/affiliates/search?${params}`)
      const result = Array.isArray(data) ? data : (data?.items ?? [])
      setAffiliates(result)
      setTotal(data?.total ?? result.length)
    } catch {
      setAffiliates([])
    } finally {
      setIsLoading(false)
    }
  }

  function resetFilters() {
    setSearchName(''); setFollowerRange({ min: '', max: '' }); setEngagementMin('')
    setCreatorCategories([]); setDeliveryCategories([]); setSalesMethods([])
    setHasWhatsapp(''); setSortBy('followers_desc'); setLocations([])
  }

  async function handleUpdateWA() {
    if (!waModal || !waInput.trim()) return
    setWaSaving(true)
    try {
      await apiClient.patch(`/affiliates/${waModal.id}/whatsapp`, {
        phone_number: waInput.trim(),
        auto_send_wa: true,
      })
      setWaSuccess(true)
      // Update local state
      setAffiliates(prev => prev.map(a =>
        a.id === waModal.id ? { ...a, has_whatsapp: true } : a
      ))
      setTimeout(() => { setWaModal(null); setWaInput(''); setWaSuccess(false) }, 1500)
    } catch {} finally { setWaSaving(false) }
  }

  async function downloadAffiliates(format: 'csv' | 'excel') {
    if (format === 'csv') {
      const headers = ['Nama', 'Followers', 'Engagement Rate', 'Lokasi', 'Kategori', 'WhatsApp']
      const rows = affiliates.map((a: any) => [
        a.name, a.follower_count, `${(a.engagement_rate * 100).toFixed(1)}%`,
        a.location, a.content_categories?.join('; ') ?? '', a.has_whatsapp ? 'Ya' : 'Tidak',
      ])
      const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = 'data-affiliasi.csv'; a.click()
      URL.revokeObjectURL(url)
    }
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div className="flex h-full gap-0">
      {/* ── Sidebar Filter ── */}
      <aside className="w-72 shrink-0 border-r border-[#1f1f1f] bg-[#0d0d0d] overflow-y-auto p-4 space-y-1">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-white">Filter Pencarian</span>
          {activeCount > 0 && (
            <button onClick={resetFilters} className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-400">
              <RotateCcw className="h-3 w-3" /> Reset ({activeCount})
            </button>
          )}
        </div>

        <FilterSection title="Nama Affiliasi" defaultOpen>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
            <input type="text" placeholder="Cari nama affiliasi..."
              value={searchName} onChange={e => setSearchName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch(1)}
              className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] pl-8 pr-3 py-2 text-xs text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
          </div>
        </FilterSection>

        <FilterSection title="Kategori Kreator" defaultOpen>
          <TagGroup items={CREATOR_CATEGORIES} selected={creatorCategories}
            onToggle={v => toggleTag(creatorCategories, setCreatorCategories, v)} />
        </FilterSection>

        <FilterSection title="Kategori Pengiriman">
          <TagGroup items={DELIVERY_CATEGORIES} selected={deliveryCategories}
            onToggle={v => toggleTag(deliveryCategories, setDeliveryCategories, v)} />
        </FilterSection>

        <FilterSection title="Metode Penjualan">
          <TagGroup items={SALES_METHODS} selected={salesMethods}
            onToggle={v => toggleTag(salesMethods, setSalesMethods, v)} />
        </FilterSection>

        <FilterSection title="Informasi Pengikut" defaultOpen>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Jumlah Followers</p>
              <RadioGroup
                items={FOLLOWER_RANGES.map(r => ({ label: r.label, value: `${r.min}|${r.max}` }))}
                selected={`${followerRange.min}|${followerRange.max}`}
                onSelect={v => { const [min, max] = v.split('|'); setFollowerRange({ min, max }) }}
              />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Min. Engagement Rate</p>
              <RadioGroup items={ENGAGEMENT_RANGES} selected={engagementMin} onSelect={setEngagementMin} />
            </div>
          </div>
        </FilterSection>

        {features.showWhatsApp && (
          <FilterSection title="Status WhatsApp">
            <RadioGroup
              items={[{ label: 'Semua', value: '' }, { label: 'Punya WA', value: 'yes' }, { label: 'Belum Ada WA', value: 'no' }]}
              selected={hasWhatsapp} onSelect={setHasWhatsapp}
            />
          </FilterSection>
        )}

        <FilterSection title="Lokasi">
          <TagGroup items={LOCATIONS} selected={locations}
            onToggle={v => toggleTag(locations, setLocations, v)} />
        </FilterSection>

        <FilterSection title="Urutkan" defaultOpen>
          <RadioGroup items={SORT_OPTIONS} selected={sortBy} onSelect={setSortBy} />
        </FilterSection>

        <div className="pt-3 space-y-2">
          <button onClick={() => handleSearch(1)}
            className="w-full rounded-lg bg-violet-600 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors flex items-center justify-center gap-2">
            <Search className="h-4 w-4" /> Cari Affiliasi
          </button>
          {affiliates.length > 0 && (
            <button onClick={() => downloadAffiliates('csv')}
              className="w-full rounded-lg border border-[#1f1f1f] py-1.5 text-xs text-gray-400 hover:text-white hover:border-violet-500/40 transition-colors">
              ↓ Download CSV
            </button>
          )}
        </div>
      </aside>

      {/* ── Main Content ── */}
      <div className="flex-1 overflow-auto p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-white">Pencarian Affiliasi</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {searched ? (isLoading ? 'Mencari...' : `${total} affiliasi ditemukan`) : 'Gunakan filter untuk mencari affiliasi'}
            </p>
          </div>
          {activeCount > 0 && (
            <div className="flex flex-wrap gap-1.5 max-w-sm justify-end">
              {creatorCategories.slice(0, 2).map(c => (
                <span key={c} className="flex items-center gap-1 rounded-full bg-violet-600/20 px-2 py-0.5 text-xs text-violet-300">
                  {c} <button onClick={() => toggleTag(creatorCategories, setCreatorCategories, c)}><X className="h-3 w-3" /></button>
                </span>
              ))}
              {creatorCategories.length > 2 && <span className="text-xs text-gray-500">+{creatorCategories.length - 2}</span>}
            </div>
          )}
        </div>

        {/* Loading skeleton */}
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-xl bg-[#111111]" />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && searched && affiliates.length === 0 && (
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-16 text-center">
            <Search className="h-10 w-10 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400">Tidak ada affiliasi yang ditemukan.</p>
            <p className="text-gray-600 text-sm mt-1">Coba perluas filter pencarian.</p>
          </div>
        )}

        {/* Initial state */}
        {!isLoading && !searched && (
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-16 text-center">
            <SlidersHorizontal className="h-10 w-10 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400">Atur filter dan klik "Cari Affiliasi"</p>
            <p className="text-gray-600 text-sm mt-1">Temukan kreator yang tepat untuk kampanye kamu</p>
          </div>
        )}

        {/* Results table */}
        {!isLoading && affiliates.length > 0 && (
          <>
            <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Nama</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Followers</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Engagement</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Lokasi</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Kategori</th>
                    {features.showWhatsApp && <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">Kontak</th>}
                  </tr>
                </thead>
                <tbody>
                  {affiliates.map((a: any, i: number) => (
                    <tr key={a.id} className={`border-b border-[#1f1f1f] hover:bg-[#111111] transition-colors cursor-pointer ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#0d0d0d]'}`}
                      onClick={() => router.push(`/affiliates/${a.id}`)}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-violet-600/20 flex items-center justify-center text-xs font-bold text-violet-400 shrink-0">
                            {a.name?.charAt(0)?.toUpperCase() ?? '?'}
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <p className="text-white font-medium text-sm">{a.name}</p>
                              {a.tiktok_username && (
                                <span className="rounded-full bg-[#1a1a1a] border border-[#2f2f2f] px-1.5 py-0.5 text-[10px] text-gray-400">
                                  TikTok
                                </span>
                              )}
                            </div>
                            {a.tiktok_username && (
                              <p className="text-gray-600 text-xs">{a.tiktok_username}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-white font-medium">{formatFollowers(a.follower_count)}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-medium ${a.engagement_rate >= 0.05 ? 'text-green-400' : a.engagement_rate >= 0.02 ? 'text-yellow-400' : 'text-gray-400'}`}>
                          {(a.engagement_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{a.location || '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {a.content_categories?.slice(0, 2).map((cat: string) => (
                            <span key={cat} className="rounded-md bg-[#1a1a1a] px-1.5 py-0.5 text-xs text-gray-400">{cat}</span>
                          ))}
                          {(a.content_categories?.length ?? 0) > 2 && (
                            <span className="text-xs text-gray-600">+{a.content_categories.length - 2}</span>
                          )}
                        </div>
                      </td>
                      {features.showWhatsApp && (
                      <td className="px-4 py-3 text-center">
                        {a.has_whatsapp ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-green-900/30 px-2 py-0.5 text-xs text-green-400">
                            <Phone className="h-3 w-3" /> WA
                          </span>
                        ) : (
                          <button onClick={() => { setWaModal({ id: a.id, name: a.name }); setWaInput('') }}
                            className="inline-flex items-center gap-1 rounded-full bg-[#1a1a1a] border border-[#2f2f2f] px-2 py-0.5 text-xs text-gray-400 hover:text-violet-400 hover:border-violet-500/40 transition-colors">
                            <Phone className="h-3 w-3" /> Input WA
                          </button>
                        )}
                      </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between text-sm text-gray-400">
              <span>Menampilkan {affiliates.length} dari {total} affiliasi</span>
              <div className="flex items-center gap-2">
                <button onClick={() => handleSearch(page - 1)} disabled={page <= 1}
                  className="rounded border border-[#1f1f1f] px-3 py-1.5 text-xs disabled:opacity-40 hover:border-violet-500 hover:text-white transition-colors disabled:cursor-not-allowed">
                  ← Sebelumnya
                </button>
                <span className="text-xs">Halaman {page} dari {totalPages || 1}</span>
                <button onClick={() => handleSearch(page + 1)} disabled={page >= totalPages}
                  className="rounded border border-[#1f1f1f] px-3 py-1.5 text-xs disabled:opacity-40 hover:border-violet-500 hover:text-white transition-colors disabled:cursor-not-allowed">
                  Berikutnya →
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modal Update WA */}
      {waModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-semibold text-white">Input Nomor WhatsApp</p>
              <button onClick={() => setWaModal(null)} className="text-gray-500 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-gray-400 mb-3">
              Affiliator: <span className="text-white font-medium">{waModal.name}</span>
            </p>
            <p className="text-xs text-gray-500 mb-3">
              Setelah nomor WA disimpan, sistem otomatis kirim pesan undangan WhatsApp.
            </p>
            {waSuccess ? (
              <div className="flex items-center gap-2 text-green-400 py-2">
                <Check className="h-4 w-4" />
                <span className="text-sm">Tersimpan! Pesan WA terkirim.</span>
              </div>
            ) : (
              <>
                <input value={waInput} onChange={e => setWaInput(e.target.value)}
                  placeholder="+6281234567890"
                  className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none mb-3" />
                <button onClick={handleUpdateWA} disabled={waSaving || !waInput.trim()}
                  className="w-full rounded-lg bg-violet-600 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40">
                  {waSaving ? 'Menyimpan...' : 'Simpan & Kirim WA'}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
