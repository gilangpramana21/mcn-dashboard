'use client'
import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Plus, Trash2, Pencil, Eye, X, Copy, Check, FileText, Clock, Tag } from 'lucide-react'

interface Template {
  id: string
  name: string
  content: string
  variables: string[]
  default_values: Record<string, string>
  version: number
  is_active: boolean
  campaign_ids: string[]
  message_type?: string
  channel?: string
  wa_category?: string | null
  created_at: string
  updated_at: string
}

const WA_CATEGORIES = [
  { value: '', label: 'Semua Kategori (Universal)' },
  { value: 'FnB', label: 'Makanan & Minuman (FnB)' },
  { value: 'Fashion', label: 'Fashion' },
  { value: 'Kecantikan', label: 'Kecantikan & Perawatan' },
  { value: 'Elektronik', label: 'Elektronik & Gadget' },
  { value: 'Olahraga', label: 'Olahraga & Kesehatan' },
  { value: 'Umum', label: 'Umum' },
]

const CATEGORY_COLORS: Record<string, string> = {
  'FnB': 'bg-orange-600/20 text-orange-400 border-orange-600/30',
  'Fashion': 'bg-pink-600/20 text-pink-400 border-pink-600/30',
  'Kecantikan': 'bg-purple-600/20 text-purple-400 border-purple-600/30',
  'Skincare': 'bg-purple-600/20 text-purple-400 border-purple-600/30',
  'Elektronik': 'bg-blue-600/20 text-blue-400 border-blue-600/30',
  'Olahraga': 'bg-green-600/20 text-green-400 border-green-600/30',
  'Umum': 'bg-gray-700/20 text-gray-400 border-gray-700/30',
}

// Jenis pesan dan channel
const MESSAGE_TYPES = [
  { value: 'campaign_invitation', label: 'Undangan Kampanye', icon: '📢', channel: 'whatsapp',
    desc: 'Undang influencer bergabung kampanye via WhatsApp' },
  { value: 'request_whatsapp', label: 'Minta Nomor WA', icon: '📱', channel: 'tiktok_chat',
    desc: 'Minta nomor WhatsApp via chat TikTok Seller Center' },
  { value: 'followup', label: 'Follow-up', icon: '🔔', channel: 'whatsapp',
    desc: 'Pengingat untuk influencer yang belum merespons' },
  { value: 'product_brief', label: 'Brief Produk', icon: '📋', channel: 'whatsapp',
    desc: 'Kirim detail produk/brief ke influencer yang sudah menerima' },
  { value: 'broadcast', label: 'Pengumuman', icon: '📣', channel: 'whatsapp',
    desc: 'Broadcast informasi umum ke semua influencer aktif' },
  { value: 'custom', label: 'Pesan Kustom', icon: '✏️', channel: 'whatsapp',
    desc: 'Pesan bebas untuk keperluan khusus' },
]

const CHANNEL_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  whatsapp: { label: 'WhatsApp', color: 'text-green-400', bg: 'bg-green-900/20 border-green-900/30' },
  tiktok_chat: { label: 'TikTok Chat', color: 'text-pink-400', bg: 'bg-pink-900/20 border-pink-900/30' },
}
function extractVariables(content: string): string[] {
  const matches = content.match(/\{\{(\w+)\}\}/g) ?? []
  return Array.from(new Set(matches.map(m => m.replace(/\{\{|\}\}/g, ''))))
}

// Preview dengan substitusi variabel
function previewContent(content: string, defaults: Record<string, string>): string {
  return content.replace(/\{\{(\w+)\}\}/g, (_, key) => defaults[key] ?? `[${key}]`)
}

// ─── Form Modal ───────────────────────────────────────────────────────────────

function TemplateModal({ template, onClose, onSave }: {
  template?: Template | null
  onClose: () => void
  onSave: () => void
}) {
  const isEdit = !!template
  const [name, setName] = useState(template?.name ?? '')
  const [content, setContent] = useState(template?.content ?? '')
  const [defaults, setDefaults] = useState<Record<string, string>>(template?.default_values ?? {})
  const [messageType, setMessageType] = useState((template as any)?.message_type ?? 'campaign_invitation')
  const [waCategory, setWaCategory] = useState(template?.wa_category ?? '')
  const [showPreview, setShowPreview] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const selectedType = MESSAGE_TYPES.find(t => t.value === messageType) ?? MESSAGE_TYPES[0]
  const variables = extractVariables(content)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (isEdit) {
        await apiClient.put(`/templates/${template!.id}`, {
          content,
          default_values: defaults,
          wa_category: waCategory || null,
        })
      } else {
        await apiClient.post('/templates', {
          name, content, default_values: defaults,
          message_type: messageType, channel: selectedType.channel,
          wa_category: waCategory || null,
        })
      }
      onSave()
      onClose()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Gagal menyimpan template')
    } finally {
      setSaving(false)
    }
  }

  function insertVariable(v: string) {
    setContent(prev => prev + `{{${v}}}`)
  }

  const COMMON_VARS = ['nama_influencer', 'nama_kampanye', 'tanggal_mulai', 'komisi', 'produk', 'brand']

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-xl border border-[#1f1f1f] bg-[#111111] shadow-2xl flex flex-col" style={{maxHeight: '90vh'}}>
        <div className="flex items-center justify-between border-b border-[#1f1f1f] px-6 py-4 shrink-0">
          <h2 className="text-base font-semibold text-white">
            {isEdit ? `Edit Template — v${template!.version}` : 'Buat Template Baru'}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X className="h-5 w-5" /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          {!isEdit && (
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Nama Template</label>
              <input value={name} onChange={e => setName(e.target.value)} required placeholder="cth: Undangan Kampanye Skincare"
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
            </div>
          )}

          {/* Jenis Pesan */}
          <div>
            <label className="text-xs font-medium text-gray-400 mb-2 block">Jenis Pesan</label>
            <div className="grid grid-cols-2 gap-2">
              {MESSAGE_TYPES.map(t => (
                <button key={t.value} type="button" onClick={() => setMessageType(t.value)}
                  className={`flex items-start gap-2 rounded-lg border p-2.5 text-left transition-colors ${
                    messageType === t.value
                      ? 'border-violet-500/60 bg-violet-500/10'
                      : 'border-[#1f1f1f] hover:border-[#2f2f2f]'
                  }`}>
                  <span className="text-base">{t.icon}</span>
                  <div>
                    <p className={`text-xs font-medium ${messageType === t.value ? 'text-violet-300' : 'text-gray-300'}`}>{t.label}</p>
                    <p className="text-xs text-gray-600 mt-0.5 leading-tight">{t.desc}</p>
                  </div>
                </button>
              ))}
            </div>
            {selectedType && (
              <div className={`mt-2 flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs ${CHANNEL_CONFIG[selectedType.channel]?.bg} ${CHANNEL_CONFIG[selectedType.channel]?.color}`}>
                <span>Dikirim via:</span>
                <span className="font-medium">{CHANNEL_CONFIG[selectedType.channel]?.label}</span>
              </div>
            )}
          </div>

          {/* Kategori WA */}
          <div>
            <label className="text-xs font-medium text-gray-400 mb-1.5 block">
              Kategori WhatsApp
              <span className="ml-1 text-gray-600 font-normal">(template ini dipakai oleh nomor WA kategori apa?)</span>
            </label>
            <div className="flex flex-wrap gap-1.5">
              {WA_CATEGORIES.map(cat => (
                <button key={cat.value} type="button" onClick={() => setWaCategory(cat.value)}
                  className={`rounded-full px-3 py-1 text-xs transition-colors border ${
                    waCategory === cat.value
                      ? 'bg-violet-600 text-white border-violet-600'
                      : 'border-[#2f2f2f] text-gray-400 hover:text-white'
                  }`}>
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-gray-400">Konten Pesan</label>
              <button type="button" onClick={() => setShowPreview(!showPreview)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-violet-400">
                <Eye className="h-3.5 w-3.5" /> {showPreview ? 'Edit' : 'Preview'}
              </button>
            </div>
            {showPreview ? (
              <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-3 text-sm text-gray-300 whitespace-pre-wrap min-h-[120px]">
                {previewContent(content, defaults) || <span className="text-gray-600">Konten kosong</span>}
              </div>
            ) : (
              <textarea value={content} onChange={e => setContent(e.target.value)} required rows={6}
                placeholder="Halo {{nama_influencer}}, kami mengundang kamu untuk bergabung dalam kampanye {{nama_kampanye}}..."
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none resize-none" />
            )}
          </div>

          {/* Quick insert variables */}
          <div>
            <p className="text-xs text-gray-500 mb-1.5">Sisipkan variabel cepat:</p>
            <div className="flex flex-wrap gap-1.5">
              {COMMON_VARS.map(v => (
                <button key={v} type="button" onClick={() => insertVariable(v)}
                  className="rounded-md bg-[#1a1a1a] px-2 py-1 text-xs text-gray-400 hover:bg-violet-600/20 hover:text-violet-300 transition-colors">
                  {`{{${v}}}`}
                </button>
              ))}
            </div>
          </div>

          {/* Detected variables & default values */}
          {variables.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-400 mb-2">Nilai default variabel:</p>
              <div className="space-y-2">
                {variables.map(v => (
                  <div key={v} className="flex items-center gap-2">
                    <span className="rounded-md bg-violet-600/20 px-2 py-1 text-xs text-violet-300 shrink-0 w-40 truncate">{`{{${v}}}`}</span>
                    <input value={defaults[v] ?? ''} onChange={e => setDefaults(d => ({ ...d, [v]: e.target.value }))}
                      placeholder={`Nilai default untuk ${v}`}
                      className="flex-1 rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && <p className="text-xs text-red-400">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={saving}
              className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
              {saving ? 'Menyimpan...' : isEdit ? 'Simpan Perubahan' : 'Buat Template'}
            </button>
            <button type="button" onClick={onClose}
              className="rounded-lg border border-[#1f1f1f] px-4 py-2 text-sm text-gray-400 hover:text-white">
              Batal
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Template Card ────────────────────────────────────────────────────────────

function TemplateCard({ template, onEdit, onDelete, onCopy }: {
  template: Template
  onEdit: () => void
  onDelete: () => void
  onCopy: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(template.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    onCopy()
  }

  const variables = extractVariables(template.content)

  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden hover:border-[#2f2f2f] transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4">
        <div className="flex items-start gap-3 min-w-0">
          <div className="mt-0.5 h-8 w-8 rounded-lg bg-violet-600/20 flex items-center justify-center shrink-0">
            <FileText className="h-4 w-4 text-violet-400" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-white font-medium truncate">{template.name}</p>
              <span className="rounded-full bg-[#1a1a1a] px-2 py-0.5 text-xs text-gray-500">v{template.version}</span>
              {template.is_active && (
                <span className="rounded-full bg-green-900/30 px-2 py-0.5 text-xs text-green-400">Aktif</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Clock className="h-3 w-3" />
                {new Date(template.updated_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
              </span>
              {variables.length > 0 && (
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <Tag className="h-3 w-3" />
                  {variables.length} variabel
                </span>
              )}
              {template.campaign_ids.length > 0 && (
                <span className="text-xs text-gray-500">{template.campaign_ids.length} kampanye</span>
              )}
            </div>
            {/* Jenis pesan & channel */}
            {(() => {
              const mt = MESSAGE_TYPES.find(t => t.value === (template as any).message_type)
              const chKey = (template as any).channel ?? 'whatsapp'
              const ch = CHANNEL_CONFIG[chKey]
              const waCat = template.wa_category
              return (
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  {mt && <span className="text-xs text-gray-500">{mt.icon} {mt.label}</span>}
                  {ch && <span className={`text-xs rounded-full border px-2 py-0.5 ${ch.bg} ${ch.color}`}>{ch.label}</span>}
                  {waCat ? (
                    <span className={`text-xs rounded-full border px-2 py-0.5 ${CATEGORY_COLORS[waCat] ?? 'bg-gray-700/20 text-gray-400 border-gray-700/30'}`}>
                      WA: {waCat}
                    </span>
                  ) : (
                    <span className="text-xs rounded-full border px-2 py-0.5 bg-gray-800/20 text-gray-600 border-gray-800/30">
                      WA: Semua
                    </span>
                  )}
                </div>
              )
            })()}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0 ml-3">
          <button onClick={handleCopy} title="Salin konten"
            className="rounded-lg p-1.5 text-gray-500 hover:bg-[#1a1a1a] hover:text-white transition-colors">
            {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
          </button>
          <button onClick={onEdit} title="Edit template"
            className="rounded-lg p-1.5 text-gray-500 hover:bg-[#1a1a1a] hover:text-white transition-colors">
            <Pencil className="h-4 w-4" />
          </button>
          <button onClick={onDelete} title="Hapus template"
            className="rounded-lg p-1.5 text-gray-500 hover:bg-red-900/20 hover:text-red-400 transition-colors">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content preview */}
      <div className="px-5 pb-4">
        <div className="rounded-lg bg-[#0a0a0a] border border-[#1a1a1a] px-4 py-3">
          <p className={`text-sm text-gray-400 whitespace-pre-wrap ${!expanded ? 'line-clamp-3' : ''}`}>
            {template.content}
          </p>
          {template.content.split('\n').length > 3 && (
            <button onClick={() => setExpanded(!expanded)}
              className="mt-2 text-xs text-violet-400 hover:text-violet-300">
              {expanded ? 'Tampilkan lebih sedikit' : 'Tampilkan semua'}
            </button>
          )}
        </div>

        {/* Variables */}
        {variables.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {variables.map(v => (
              <span key={v} className="rounded-md bg-violet-600/10 border border-violet-600/20 px-2 py-0.5 text-xs text-violet-400">
                {`{{${v}}}`}
                {template.default_values[v] && (
                  <span className="text-violet-600 ml-1">= {template.default_values[v]}</span>
                )}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editTemplate, setEditTemplate] = useState<Template | null>(null)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')

  async function load() {
    setIsLoading(true)
    try {
      const { data } = await apiClient.get('/templates')
      setTemplates(Array.isArray(data) ? data : (data.templates ?? []))
    } catch { setTemplates([]) }
    finally { setIsLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id: string) {
    if (!confirm('Hapus template ini?')) return
    try { await apiClient.delete(`/templates/${id}`); load() } catch {}
  }

  function openCreate() { setEditTemplate(null); setShowModal(true) }
  function openEdit(t: Template) { setEditTemplate(t); setShowModal(true) }

  const filtered = templates.filter(t => {
    const matchSearch = t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.content.toLowerCase().includes(search.toLowerCase())
    const matchCategory = !categoryFilter ||
      (categoryFilter === 'universal' ? !t.wa_category : t.wa_category === categoryFilter)
    return matchSearch && matchCategory
  })

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Template Pesan</h1>
          <p className="text-sm text-gray-500 mt-0.5">{templates.length} template tersedia</p>
        </div>
        <div className="flex items-center gap-3">
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Cari template..."
            className="rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none w-52" />
          <div className="flex rounded-lg border border-[#1f1f1f] overflow-hidden">
            {[
              { value: '', label: 'Semua' },
              { value: 'universal', label: 'Universal' },
              { value: 'FnB', label: 'Makanan & Minuman' },
              { value: 'Fashion', label: 'Fashion' },
              { value: 'Kecantikan', label: 'Kecantikan' },
              { value: 'Elektronik', label: 'Elektronik' },
              { value: 'Olahraga', label: 'Olahraga' },
            ].map(f => (
              <button key={f.value} onClick={() => setCategoryFilter(f.value)}
                className={`px-3 py-1.5 text-xs transition-colors ${categoryFilter === f.value ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                {f.label}
              </button>
            ))}
          </div>
          <button onClick={openCreate}
            className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
            <Plus className="h-4 w-4" /> Buat Template
          </button>
        </div>
      </div>

      {/* Stats */}
      {templates.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <p className="text-xs text-gray-500">Total Template</p>
            <p className="text-2xl font-bold text-white mt-1">{templates.length}</p>
          </div>
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <p className="text-xs text-gray-500">Template Aktif</p>
            <p className="text-2xl font-bold text-green-400 mt-1">{templates.filter(t => t.is_active).length}</p>
          </div>
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <p className="text-xs text-gray-500">Digunakan Kampanye</p>
            <p className="text-2xl font-bold text-violet-400 mt-1">{templates.filter(t => t.campaign_ids.length > 0).length}</p>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-[#111111]" />
          ))}
        </div>
      )}

      {/* Empty */}
      {!isLoading && templates.length === 0 && (
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-16 text-center">
          <FileText className="h-12 w-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400 font-medium">Belum ada template</p>
          <p className="text-gray-600 text-sm mt-1">Buat template pertama untuk mulai mengirim undangan</p>
          <button onClick={openCreate}
            className="mt-4 rounded-lg bg-violet-600 px-5 py-2 text-sm text-white hover:bg-violet-700">
            Buat Template
          </button>
        </div>
      )}

      {/* Template list */}
      {!isLoading && filtered.length > 0 && (
        <div className="space-y-3">
          {filtered.map(t => (
            <TemplateCard key={t.id} template={t}
              onEdit={() => openEdit(t)}
              onDelete={() => handleDelete(t.id)}
              onCopy={() => {}}
            />
          ))}
        </div>
      )}

      {!isLoading && search && filtered.length === 0 && (
        <p className="text-gray-500 text-sm text-center py-8">Tidak ada template yang cocok dengan "{search}"</p>
      )}

      {/* Modal */}
      {showModal && (
        <TemplateModal template={editTemplate} onClose={() => setShowModal(false)} onSave={load} />
      )}
    </div>
  )
}
