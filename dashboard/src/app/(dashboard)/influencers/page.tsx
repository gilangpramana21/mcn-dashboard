'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAffiliates } from '@/hooks/useAffiliates'
import { InfluencerTable, toggleSortDirection } from '@/components/InfluencerTable'
import type { SortField, SortDirection } from '@/components/InfluencerTable'
import type { InfluencerFilters } from '@/types/api'
import { apiClient } from '@/lib/api-client'
import { ChevronDown, ChevronUp, X, Search, RotateCcw } from 'lucide-react'

const DEFAULT_PAGE_SIZE = 20

// ─── Filter Data ─────────────────────────────────────────────────────────────

const CREATOR_CATEGORIES = [
  'Kecantikan & Perawatan', 'Fashion Wanita', 'Fashion Pria', 'Aksesoris Fashion',
  'Makanan & Minuman', 'Kesehatan & Suplemen', 'Skincare', 'Perawatan Rambut',
  'Rumah Tangga', 'Elektronik & Gadget', 'Olahraga & Outdoor', 'Gaming',
  'Anak & Bayi', 'Hewan Peliharaan', 'Otomotif', 'Travel & Lifestyle',
  'Kuliner & Resep', 'Motivasi & Bisnis', 'Hiburan & Komedi', 'Musik & Seni',
  'Edukasi', 'Teknologi', 'Keuangan & Investasi',
]

const DELIVERY_CATEGORIES = [
  'Pengiriman Cepat (Same Day)', 'Pengiriman Reguler', 'Pengiriman Gratis',
  'COD (Bayar di Tempat)', 'Pengiriman Internasional', 'Pickup di Toko',
]

const SALES_METHODS = [
  'Live Shopping', 'Video Pendek', 'Story / Reels', 'Konten Organik',
  'Paid Promotion', 'Affiliate Link', 'Bundle Deal', 'Flash Sale',
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

const CREATOR_FILTERS = [
  { label: 'Semua Kreator', value: '' },
  { label: 'Punya WhatsApp', value: 'has_whatsapp' },
  { label: 'Sudah Diundang', value: 'invited' },
  { label: 'Sudah Menerima', value: 'accepted' },
  { label: 'Belum Diundang', value: 'not_invited' },
]

const SELECTED_CONDITIONS = [
  { label: 'Semua', value: '' },
  { label: 'Relevansi Tertinggi', value: 'relevance_desc' },
  { label: 'Followers Terbanyak', value: 'followers_desc' },
  { label: 'Engagement Tertinggi', value: 'engagement_desc' },
  { label: 'Terbaru Bergabung', value: 'newest' },
]

const LOCATIONS = [
  'Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Semarang',
  'Makassar', 'Palembang', 'Tangerang', 'Depok', 'Bekasi',
  'Yogyakarta', 'Bali', 'Bogor', 'Malang', 'Batam',
]

// ─── Section Component ────────────────────────────────────────────────────────

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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InfluencersPage() {
  const router = useRouter()

  const [filters, setFilters] = useState<InfluencerFilters>({ page: 1, page_size: DEFAULT_PAGE_SIZE })
  const [sortField, setSortField] = useState<SortField>('follower_count')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  // Filter state
  const [searchName, setSearchName] = useState('')
  const [followerRange, setFollowerRange] = useState({ min: '', max: '' })
  const [engagementMin, setEngagementMin] = useState('')
  const [creatorCategories, setCreatorCategories] = useState<string[]>([])
  const [deliveryCategories, setDeliveryCategories] = useState<string[]>([])
  const [salesMethods, setSalesMethods] = useState<string[]>([])
  const [creatorFilter, setCreatorFilter] = useState('')
  const [selectedCondition, setSelectedCondition] = useState('')
  const [locations, setLocations] = useState<string[]>([])

  const { data, isLoading } = useAffiliates(filters)
  const items = data?.data?.items ?? []
  const total = data?.data?.total ?? 0
  const totalPages = Math.ceil(total / DEFAULT_PAGE_SIZE)
  const currentPage = filters.page
  const startItem = total === 0 ? 0 : (currentPage - 1) * DEFAULT_PAGE_SIZE + 1
  const endItem = Math.min(currentPage * DEFAULT_PAGE_SIZE, total)

  const activeCount = [
    searchName, followerRange.min || followerRange.max, engagementMin,
    ...creatorCategories, ...deliveryCategories, ...salesMethods,
    creatorFilter, selectedCondition, ...locations,
  ].filter(Boolean).length

  function toggleTag(list: string[], setList: (v: string[]) => void, val: string) {
    setList(list.includes(val) ? list.filter(x => x !== val) : [...list, val])
  }

  function applyFilters() {
    setFilters({
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
      name: searchName || undefined,
      min_followers: followerRange.min ? Number(followerRange.min) : undefined,
      max_followers: followerRange.max ? Number(followerRange.max) : undefined,
      min_engagement_rate: engagementMin ? Number(engagementMin) : undefined,
      categories: creatorCategories.length ? creatorCategories : undefined,
      delivery_categories: deliveryCategories.length ? deliveryCategories : undefined,
      sales_methods: salesMethods.length ? salesMethods : undefined,
      has_whatsapp: creatorFilter === 'has_whatsapp' ? true : undefined,
      invitation_status: ['invited', 'accepted', 'not_invited'].includes(creatorFilter) ? creatorFilter : undefined,
      locations: locations.length ? locations : undefined,
      sort_by: selectedCondition || undefined,
    })
  }

  function resetFilters() {
    setSearchName(''); setFollowerRange({ min: '', max: '' }); setEngagementMin('')
    setCreatorCategories([]); setDeliveryCategories([]); setSalesMethods([])
    setCreatorFilter(''); setSelectedCondition(''); setLocations([])
    setFilters({ page: 1, page_size: DEFAULT_PAGE_SIZE })
  }

  function handleSort(field: SortField) {
    const newDir = toggleSortDirection(field, sortField, sortDirection)
    setSortField(field); setSortDirection(newDir)
  }

  async function downloadInfluencers(format: 'csv' | 'excel') {
    try {
      const response = await apiClient.post('/reports/export', { format }, { responseType: 'blob' })
      const blob = new Blob([response.data as BlobPart])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `data-influencer.${format === 'excel' ? 'xlsx' : 'csv'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

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

        {/* Nama Panggilan */}
        <FilterSection title="Nama Panggilan" defaultOpen>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
            <input
              type="text" placeholder="Cari nama kreator..."
              value={searchName} onChange={e => setSearchName(e.target.value)}
              className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] pl-8 pr-3 py-2 text-xs text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none"
            />
          </div>
        </FilterSection>

        {/* Kategori Kreator */}
        <FilterSection title="Kategori Kreator" defaultOpen>
          <TagGroup items={CREATOR_CATEGORIES} selected={creatorCategories}
            onToggle={v => toggleTag(creatorCategories, setCreatorCategories, v)} />
        </FilterSection>

        {/* Kategori Pengiriman */}
        <FilterSection title="Kategori Pengiriman">
          <TagGroup items={DELIVERY_CATEGORIES} selected={deliveryCategories}
            onToggle={v => toggleTag(deliveryCategories, setDeliveryCategories, v)} />
        </FilterSection>

        {/* Metode Penjualan Produk */}
        <FilterSection title="Metode Penjualan Produk">
          <TagGroup items={SALES_METHODS} selected={salesMethods}
            onToggle={v => toggleTag(salesMethods, setSalesMethods, v)} />
        </FilterSection>

        {/* Filter Kreator */}
        <FilterSection title="Filter Kreator">
          <RadioGroup items={CREATOR_FILTERS} selected={creatorFilter} onSelect={setCreatorFilter} />
        </FilterSection>

        {/* Informasi Pengikut */}
        <FilterSection title="Informasi Pengikut" defaultOpen>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Jumlah Followers</p>
              <RadioGroup
                items={FOLLOWER_RANGES.map(r => ({ label: r.label, value: `${r.min}|${r.max}` }))}
                selected={`${followerRange.min}|${followerRange.max}`}
                onSelect={v => {
                  const [min, max] = v.split('|')
                  setFollowerRange({ min, max })
                }}
              />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Min. Engagement Rate</p>
              <RadioGroup items={ENGAGEMENT_RANGES} selected={engagementMin} onSelect={setEngagementMin} />
            </div>
          </div>
        </FilterSection>

        {/* Penyaringan Data (Lokasi) */}
        <FilterSection title="Penyaringan Data (Lokasi)">
          <TagGroup items={LOCATIONS} selected={locations}
            onToggle={v => toggleTag(locations, setLocations, v)} />
        </FilterSection>

        {/* Kondisi Terpilih */}
        <FilterSection title="Kondisi Terpilih">
          <RadioGroup items={SELECTED_CONDITIONS} selected={selectedCondition} onSelect={setSelectedCondition} />
        </FilterSection>

        {/* Tombol Aksi */}
        <div className="pt-3 space-y-2">
          <button onClick={applyFilters}
            className="w-full rounded-lg bg-violet-600 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
            Terapkan Filter
          </button>
          <div className="flex gap-2">
            <button onClick={() => downloadInfluencers('csv')}
              className="flex-1 rounded-lg border border-[#1f1f1f] py-1.5 text-xs text-gray-400 hover:text-white hover:border-violet-500/40 transition-colors">
              ↓ CSV
            </button>
            <button onClick={() => downloadInfluencers('excel')}
              className="flex-1 rounded-lg border border-[#1f1f1f] py-1.5 text-xs text-gray-400 hover:text-white hover:border-violet-500/40 transition-colors">
              ↓ Excel
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <div className="flex-1 overflow-auto p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-white">Daftar Influencer</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {total > 0 ? `${total} kreator ditemukan` : 'Gunakan filter untuk mencari kreator'}
            </p>
          </div>
          {/* Active filter tags */}
          {activeCount > 0 && (
            <div className="flex flex-wrap gap-1.5 max-w-md justify-end">
              {creatorCategories.slice(0, 3).map(c => (
                <span key={c} className="flex items-center gap-1 rounded-full bg-violet-600/20 px-2 py-0.5 text-xs text-violet-300">
                  {c} <button onClick={() => toggleTag(creatorCategories, setCreatorCategories, c)}><X className="h-3 w-3" /></button>
                </span>
              ))}
              {creatorCategories.length > 3 && (
                <span className="text-xs text-gray-500">+{creatorCategories.length - 3} lagi</span>
              )}
            </div>
          )}
        </div>

        <InfluencerTable
          data={items} isLoading={isLoading}
          onRowClick={id => router.push(`/influencers/${id}`)}
          sortField={sortField} sortDirection={sortDirection} onSort={handleSort}
        />

        {/* Pagination */}
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>
            {total > 0 ? `Menampilkan ${startItem}–${endItem} dari ${total}` : 'Tidak ada data'}
          </span>
          <div className="flex items-center gap-2">
            <button onClick={() => setFilters(p => ({ ...p, page: p.page - 1 }))}
              disabled={currentPage <= 1}
              className="rounded border border-[#1f1f1f] px-3 py-1.5 text-xs disabled:opacity-40 hover:border-violet-500 hover:text-white transition-colors disabled:cursor-not-allowed">
              ← Sebelumnya
            </button>
            <span className="text-xs">Halaman {currentPage} dari {totalPages || 1}</span>
            <button onClick={() => setFilters(p => ({ ...p, page: p.page + 1 }))}
              disabled={currentPage >= totalPages}
              className="rounded border border-[#1f1f1f] px-3 py-1.5 text-xs disabled:opacity-40 hover:border-violet-500 hover:text-white transition-colors disabled:cursor-not-allowed">
              Berikutnya →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
