'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { Plus, Download, ChevronDown, ChevronUp, FileSpreadsheet, BarChart2, Trash2 } from 'lucide-react'
import Link from 'next/link'

interface Brand {
  id: string
  name: string
  wa_number: string | null
  sow: string | null
  message_template: string | null
  sku_count: number
}

interface BrandSKU {
  id: string
  product_name: string
  affiliate_link: string | null
  price: number
}

function formatRupiah(n: number) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(n)
}

export default function BrandsPage() {
  const qc = useQueryClient()
  const [expandedBrand, setExpandedBrand] = useState<string | null>(null)
  const [showAddBrand, setShowAddBrand] = useState(false)
  const [showAddSKU, setShowAddSKU] = useState<string | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)

  const [brandForm, setBrandForm] = useState({ name: '', wa_number: '', sow: '', message_template: '' })
  const [skuForm, setSkuForm] = useState({ product_name: '', affiliate_link: '', price: '' })

  const { data: brands = [], isLoading } = useQuery({
    queryKey: ['brands'],
    queryFn: () => apiClient.get('/brands').then(r => (r as any).data ?? r),
  })

  const { data: skus = [] } = useQuery({
    queryKey: ['brand-skus', expandedBrand],
    queryFn: () => expandedBrand
      ? apiClient.get(`/brands/${expandedBrand}/skus`).then(r => (r as any).data ?? r)
      : [],
    enabled: !!expandedBrand,
  })

  const createBrand = useMutation({
    mutationFn: (data: typeof brandForm) => apiClient.post('/brands', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['brands'] }); setShowAddBrand(false); setBrandForm({ name: '', wa_number: '', sow: '', message_template: '' }) },
  })

  const createSKU = useMutation({
    mutationFn: ({ brandId, data }: { brandId: string; data: typeof skuForm }) =>
      apiClient.post(`/brands/${brandId}/skus`, { ...data, price: parseInt(data.price) || 0 }),
    onSuccess: (_, { brandId }) => {
      qc.invalidateQueries({ queryKey: ['brand-skus', brandId] })
      qc.invalidateQueries({ queryKey: ['brands'] })
      setShowAddSKU(null)
      setSkuForm({ product_name: '', affiliate_link: '', price: '' })
    },
  })

  const deleteBrand = useMutation({
    mutationFn: (brandId: string) => apiClient.delete(`/brands/${brandId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brands'] }),
  })

  async function downloadExcel(type: 'outreach' | 'deal' | 'master-brand', brandId?: string) {
    setDownloading(type)
    try {
      const params = brandId ? `?brand_id=${brandId}` : ''
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/brands/export/${type}${params}`,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      )
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${type}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error(e)
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Manajemen Brand</h1>
          <p className="text-sm text-gray-500 mt-0.5">Kelola brand, SKU affiliasi, SOW, dan export laporan</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => downloadExcel('master-brand')}
            disabled={downloading === 'master-brand'}
            className="flex items-center gap-1.5 rounded-lg border border-[#2f2f2f] px-3 py-2 text-sm text-gray-300 hover:text-white hover:border-teal-500 transition-colors disabled:opacity-50"
          >
            <FileSpreadsheet className="h-4 w-4 text-teal-400" />
            {downloading === 'master-brand' ? 'Mengunduh...' : 'Export Master Brand'}
          </button>
          <button
            onClick={() => downloadExcel('outreach')}
            disabled={downloading === 'outreach'}
            className="flex items-center gap-1.5 rounded-lg border border-[#2f2f2f] px-3 py-2 text-sm text-gray-300 hover:text-white hover:border-yellow-500 transition-colors disabled:opacity-50"
          >
            <Download className="h-4 w-4 text-yellow-400" />
            {downloading === 'outreach' ? 'Mengunduh...' : 'Export Outreach'}
          </button>
          <button
            onClick={() => downloadExcel('deal')}
            disabled={downloading === 'deal'}
            className="flex items-center gap-1.5 rounded-lg border border-[#2f2f2f] px-3 py-2 text-sm text-gray-300 hover:text-white hover:border-green-500 transition-colors disabled:opacity-50"
          >
            <Download className="h-4 w-4 text-green-400" />
            {downloading === 'deal' ? 'Mengunduh...' : 'Export Deal'}
          </button>
          <button
            onClick={() => setShowAddBrand(true)}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm text-white hover:bg-violet-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Tambah Brand
          </button>
        </div>
      </div>

      {/* Add Brand Form */}
      {showAddBrand && (
        <div className="rounded-xl border border-violet-500/30 bg-[#111111] p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Tambah Brand Baru</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Nama Brand</label>
              <input value={brandForm.name} onChange={e => setBrandForm(p => ({ ...p, name: e.target.value }))}
                placeholder="contoh: VARESSE" className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">No WA yang Dipakai</label>
              <input value={brandForm.wa_number} onChange={e => setBrandForm(p => ({ ...p, wa_number: e.target.value }))}
                placeholder="628xxx" className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">SOW (Statement of Work)</label>
            <textarea value={brandForm.sow} onChange={e => setBrandForm(p => ({ ...p, sow: e.target.value }))}
              rows={3} placeholder="Sistem: Video only&#10;Minimal GMV: Rp10 juta&#10;Rata-rata video views: 400-500&#10;Kategori: Kecantikan"
              className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none resize-none" />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Template Pesan WA</label>
            <textarea value={brandForm.message_template} onChange={e => setBrandForm(p => ({ ...p, message_template: e.target.value }))}
              rows={3} placeholder="Halo kak {{nama_creator}}, kami dari MCN Asia ingin mengajak kolaborasi dengan brand {{brand}}..."
              className="w-full rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none resize-none" />
          </div>
          <div className="flex gap-2">
            <button onClick={() => createBrand.mutate(brandForm)} disabled={!brandForm.name || createBrand.isPending}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700 disabled:opacity-40 transition-colors">
              {createBrand.isPending ? 'Menyimpan...' : 'Simpan Brand'}
            </button>
            <button onClick={() => setShowAddBrand(false)} className="rounded-lg border border-[#2f2f2f] px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
              Batal
            </button>
          </div>
        </div>
      )}

      {/* Brand List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <div key={i} className="h-16 animate-pulse rounded-xl bg-[#1a1a1a]" />)}
        </div>
      ) : brands.length === 0 ? (
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-12 text-center">
          <p className="text-gray-500">Belum ada brand. Tambahkan brand pertama.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {(brands as Brand[]).map(brand => (
            <div key={brand.id} className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
              {/* Brand Header */}
              <div className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center gap-4">
                  <div className="h-9 w-9 rounded-lg bg-violet-600/20 border border-violet-600/30 flex items-center justify-center">
                    <span className="text-xs font-bold text-violet-400">{brand.name.charAt(0)}</span>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{brand.name}</p>
                    <p className="text-xs text-gray-500">
                      {brand.sku_count} SKU
                      {brand.wa_number && <span> · WA: {brand.wa_number}</span>}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => downloadExcel('outreach', brand.id)}
                    className="rounded-lg border border-[#2f2f2f] px-2.5 py-1.5 text-xs text-gray-400 hover:text-yellow-400 hover:border-yellow-500/50 transition-colors"
                  >
                    Outreach
                  </button>
                  <button
                    onClick={() => downloadExcel('deal', brand.id)}
                    className="rounded-lg border border-[#2f2f2f] px-2.5 py-1.5 text-xs text-gray-400 hover:text-green-400 hover:border-green-500/50 transition-colors"
                  >
                    Deal
                  </button>
                  <Link
                    href={`/brands/${brand.id}/monthly-report`}
                    className="rounded-lg border border-[#2f2f2f] px-2.5 py-1.5 text-xs text-gray-400 hover:text-violet-400 hover:border-violet-500/50 transition-colors flex items-center gap-1"
                  >
                    <BarChart2 className="h-3 w-3" /> Monthly Report
                  </Link>
                  <button
                    onClick={() => {
                      if (confirm(`Hapus brand "${brand.name}"? Semua data terkait akan ikut terhapus.`)) {
                        deleteBrand.mutate(brand.id)
                      }
                    }}
                    className="rounded-lg border border-[#2f2f2f] p-1.5 text-gray-400 hover:text-red-400 hover:border-red-500/50 transition-colors"
                    title="Hapus brand"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setExpandedBrand(expandedBrand === brand.id ? null : brand.id)}
                    className="rounded-lg border border-[#2f2f2f] p-1.5 text-gray-400 hover:text-white transition-colors"
                  >
                    {expandedBrand === brand.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>                </div>
              </div>

              {/* Expanded Detail */}
              {expandedBrand === brand.id && (
                <div className="border-t border-[#1f1f1f] px-5 py-4 space-y-4">
                  {/* SOW */}
                  {brand.sow && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">SOW</p>
                      <p className="text-xs text-gray-300 whitespace-pre-line bg-[#0a0a0a] rounded-lg p-3 border border-[#1f1f1f]">{brand.sow}</p>
                    </div>
                  )}

                  {/* Template Pesan */}
                  {brand.message_template && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Template Pesan WA</p>
                      <p className="text-xs text-gray-300 whitespace-pre-line bg-[#0a0a0a] rounded-lg p-3 border border-[#1f1f1f]">{brand.message_template}</p>
                    </div>
                  )}

                  {/* SKU List */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-medium text-gray-500">SKU Affiliasi</p>
                      <button onClick={() => setShowAddSKU(brand.id)}
                        className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300 transition-colors">
                        <Plus className="h-3 w-3" /> Tambah SKU
                      </button>
                    </div>

                    {showAddSKU === brand.id && (
                      <div className="rounded-lg border border-violet-500/30 bg-[#0a0a0a] p-3 mb-3 space-y-2">
                        <input value={skuForm.product_name} onChange={e => setSkuForm(p => ({ ...p, product_name: e.target.value }))}
                          placeholder="Nama produk" className="w-full rounded-lg border border-[#2f2f2f] bg-[#111111] px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
                        <input value={skuForm.affiliate_link} onChange={e => setSkuForm(p => ({ ...p, affiliate_link: e.target.value }))}
                          placeholder="Link affiliasi (https://affiliate-id.tokopedia.com/...)" className="w-full rounded-lg border border-[#2f2f2f] bg-[#111111] px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
                        <input value={skuForm.price} onChange={e => setSkuForm(p => ({ ...p, price: e.target.value }))}
                          placeholder="Harga (Rp)" type="number" className="w-full rounded-lg border border-[#2f2f2f] bg-[#111111] px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
                        <div className="flex gap-2">
                          <button onClick={() => createSKU.mutate({ brandId: brand.id, data: skuForm })}
                            disabled={!skuForm.product_name || createSKU.isPending}
                            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-700 disabled:opacity-40 transition-colors">
                            Simpan
                          </button>
                          <button onClick={() => setShowAddSKU(null)} className="text-xs text-gray-500 hover:text-white transition-colors">Batal</button>
                        </div>
                      </div>
                    )}

                    {(skus as BrandSKU[]).length === 0 ? (
                      <p className="text-xs text-gray-600 py-2">Belum ada SKU</p>
                    ) : (
                      <div className="space-y-2">
                        {(skus as BrandSKU[]).map(sku => (
                          <div key={sku.id} className="flex items-start justify-between rounded-lg bg-[#0a0a0a] border border-[#1f1f1f] px-3 py-2">
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium text-white">{sku.product_name}</p>
                              {sku.affiliate_link && (
                                <a href={sku.affiliate_link} target="_blank" rel="noopener noreferrer"
                                  className="text-xs text-teal-400 hover:underline truncate block max-w-xs">
                                  {sku.affiliate_link}
                                </a>
                              )}
                              {sku.price > 0 && <p className="text-xs text-gray-500 mt-0.5">{formatRupiah(sku.price)}</p>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
