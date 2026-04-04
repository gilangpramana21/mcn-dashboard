'use client'
import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Plus, Trash2, ShieldOff, Search, AlertTriangle, X, Calendar, User } from 'lucide-react'

interface BlacklistItem {
  id: string
  influencer_id: string
  reason: string
  added_by: string
  added_at: string
  removed_at?: string
}

const REASON_PRESETS = [
  'Konten tidak sesuai panduan', 'Engagement palsu / bot', 'Tidak profesional',
  'Melanggar kontrak', 'Spam / promosi berlebihan', 'Konten negatif / kontroversial',
  'Tidak responsif', 'Penipuan', 'Lainnya',
]

export default function BlacklistPage() {
  const [list, setList] = useState<BlacklistItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState({ influencer_id: '', reason: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setIsLoading(true)
    try {
      const { data } = await apiClient.get('/influencers/blacklist')
      setList(Array.isArray(data) ? data : (data.blacklist ?? []))
    } catch { setList([]) }
    finally { setIsLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await apiClient.post('/influencers/blacklist', form)
      setForm({ influencer_id: '', reason: '' })
      setShowModal(false)
      load()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Gagal menambahkan ke daftar hitam')
    } finally { setSaving(false) }
  }

  async function handleRemove(id: string) {
    if (!confirm('Hapus dari daftar hitam?')) return
    try { await apiClient.delete(`/influencers/blacklist/${id}`); load() } catch {}
  }

  async function downloadCSV() {
    const headers = ['ID Influencer', 'Alasan', 'Tanggal Ditambahkan']
    const rows = list.map(i => [i.influencer_id, i.reason, new Date(i.added_at).toLocaleDateString('id-ID')])
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'daftar-hitam.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  const filtered = list.filter(item =>
    item.influencer_id.toLowerCase().includes(search.toLowerCase()) ||
    item.reason.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Daftar Hitam Influencer</h1>
          <p className="text-sm text-gray-500 mt-0.5">{list.length} influencer diblokir</p>
        </div>
        <div className="flex items-center gap-3">
          {list.length > 0 && (
            <button onClick={downloadCSV}
              className="rounded-lg border border-[#1f1f1f] px-3 py-2 text-xs text-gray-400 hover:text-white hover:border-violet-500/40 transition-colors">
              ↓ CSV
            </button>
          )}
          <button onClick={() => setShowModal(true)}
            className="flex items-center gap-2 rounded-lg bg-red-600/80 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 transition-colors">
            <Plus className="h-4 w-4" /> Tambah ke Daftar Hitam
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
          <p className="text-xs text-gray-500">Total Diblokir</p>
          <p className="text-2xl font-bold text-red-400 mt-1">{list.length}</p>
        </div>
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
          <p className="text-xs text-gray-500">Ditambahkan Bulan Ini</p>
          <p className="text-2xl font-bold text-white mt-1">
            {list.filter(i => {
              const d = new Date(i.added_at)
              const now = new Date()
              return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
            }).length}
          </p>
        </div>
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
          <p className="text-xs text-gray-500">Alasan Terbanyak</p>
          <p className="text-sm font-medium text-white mt-1 truncate">
            {list.length > 0 ? (() => {
              const counts: Record<string, number> = {}
              list.forEach(i => { counts[i.reason] = (counts[i.reason] ?? 0) + 1 })
              return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—'
            })() : '—'}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" />
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Cari ID influencer atau alasan..."
          className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] pl-9 pr-4 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-[#111111]" />)}
        </div>
      )}

      {/* Empty */}
      {!isLoading && list.length === 0 && (
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-16 text-center">
          <ShieldOff className="h-12 w-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400 font-medium">Daftar hitam kosong</p>
          <p className="text-gray-600 text-sm mt-1">Influencer yang diblokir akan muncul di sini</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && filtered.length > 0 && (
        <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Influencer</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Alasan Pemblokiran</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Tanggal</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, i) => (
                <tr key={item.id} className={`border-b border-[#1f1f1f] hover:bg-[#111111] transition-colors ${i % 2 === 0 ? 'bg-[#0a0a0a]' : 'bg-[#0d0d0d]'}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-7 w-7 rounded-full bg-red-900/30 flex items-center justify-center shrink-0">
                        <User className="h-3.5 w-3.5 text-red-400" />
                      </div>
                      <span className="text-white font-medium text-sm font-mono">{item.influencer_id}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
                      <span className="text-gray-300 text-sm">{item.reason}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-gray-500 text-xs">
                      <Calendar className="h-3 w-3" />
                      {item.added_at ? new Date(item.added_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button onClick={() => handleRemove(item.id)}
                      className="rounded-lg px-3 py-1 text-xs text-gray-500 hover:bg-red-900/20 hover:text-red-400 transition-colors border border-transparent hover:border-red-900/30">
                      Hapus
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isLoading && search && filtered.length === 0 && (
        <p className="text-gray-500 text-sm text-center py-8">Tidak ada hasil untuk "{search}"</p>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-[#1f1f1f] bg-[#111111] shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1f1f1f] px-6 py-4">
              <h2 className="text-base font-semibold text-white">Tambah ke Daftar Hitam</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            <form onSubmit={handleAdd} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 mb-1 block">ID Influencer</label>
                <input value={form.influencer_id} onChange={e => setForm(f => ({ ...f, influencer_id: e.target.value }))} required
                  placeholder="Masukkan ID influencer"
                  className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-red-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400 mb-1 block">Alasan Pemblokiran</label>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {REASON_PRESETS.map(r => (
                    <button key={r} type="button" onClick={() => setForm(f => ({ ...f, reason: r }))}
                      className={`rounded-full px-2.5 py-1 text-xs transition-colors ${form.reason === r ? 'bg-red-600/80 text-white' : 'border border-[#2f2f2f] text-gray-400 hover:text-white'}`}>
                      {r}
                    </button>
                  ))}
                </div>
                <input value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} required
                  placeholder="Atau tulis alasan kustom..."
                  className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-red-500 focus:outline-none" />
              </div>
              {error && <p className="text-xs text-red-400">{error}</p>}
              <div className="flex gap-3 pt-1">
                <button type="submit" disabled={saving}
                  className="rounded-lg bg-red-600/80 px-5 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50">
                  {saving ? 'Menyimpan...' : 'Tambahkan'}
                </button>
                <button type="button" onClick={() => setShowModal(false)}
                  className="rounded-lg border border-[#1f1f1f] px-4 py-2 text-sm text-gray-400 hover:text-white">
                  Batal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
