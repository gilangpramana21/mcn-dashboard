'use client'
import { useState, useEffect, useRef, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { Search, Send, MessageCircle, Phone, Settings, FileText, X, Zap, Users, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

interface Conversation {
  affiliate_id: string
  affiliate_name: string
  last_message: string
  last_message_at: string
  message_count: number
  unread_count: number
  wa_category: string | null
  has_whatsapp: boolean
}

interface Message {
  id: string
  affiliate_id: string
  affiliate_name: string
  direction: 'outbound' | 'inbound'
  message_content: string
  from_number: string | null
  to_number: string | null
  status: string
  sent_at: string
  wa_category: string | null
}

interface WaNumber {
  id: string
  category: string
  phone_number: string
  display_name: string | null
  is_active: boolean
}

interface MessageTemplate {
  id: string
  name: string
  content: string
  wa_category: string | null
  variables: string[]
  default_values: Record<string, string>
}

interface BlastRecipient {
  affiliate_id: string
  affiliate_name: string
  phone_number: string | null
  wa_category: string
}

interface BlastResult {
  total: number
  sent: number
  failed: number
  skipped: number
  recipients: BlastRecipient[]
}

const CATEGORY_COLORS: Record<string, string> = {
  'FnB': 'bg-orange-600/20 text-orange-400',
  'Fashion': 'bg-pink-600/20 text-pink-400',
  'Kecantikan': 'bg-purple-600/20 text-purple-400',
  'Skincare': 'bg-purple-600/20 text-purple-400',
  'Elektronik': 'bg-blue-600/20 text-blue-400',
  'Olahraga': 'bg-green-600/20 text-green-400',
  'Umum': 'bg-gray-700/20 text-gray-400',
}

function formatTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 86400000) return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
  if (diff < 604800000) return d.toLocaleDateString('id-ID', { weekday: 'short' })
  return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })
}

export default function MessagesPage() {
  return (
    <Suspense fallback={null}>
      <MessagesContent />
    </Suspense>
  )
}

function MessagesContent() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [selected, setSelected] = useState<Conversation | null>(null)
  const [search, setSearch] = useState('')
  const [newMsg, setNewMsg] = useState('')
  const [sending, setSending] = useState(false)
  const [showWaSettings, setShowWaSettings] = useState(false)
  const [waNumbers, setWaNumbers] = useState<WaNumber[]>([])
  const [loadingConvs, setLoadingConvs] = useState(true)
  const [templates, setTemplates] = useState<MessageTemplate[]>([])
  const [showTemplates, setShowTemplates] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const searchParams = useSearchParams()
  const autoSelectDone = useRef(false)

  // Blast state
  const [showBlast, setShowBlast] = useState(false)
  const [blastCategory, setBlastCategory] = useState('')
  const [blastMessage, setBlastMessage] = useState('')
  const [blastTemplateId, setBlastTemplateId] = useState<string | null>(null)
  const [blastPreview, setBlastPreview] = useState<BlastRecipient[] | null>(null)
  const [blastResult, setBlastResult] = useState<BlastResult | null>(null)
  const [blastLoading, setBlastLoading] = useState(false)
  const [blastStep, setBlastStep] = useState<'compose' | 'preview' | 'result'>('compose')

  useEffect(() => {
    loadConversations()
    loadWaNumbers()
    loadTemplates()
  }, [])

  // Auto-select conversation dari query param ?affiliate=nama
  // Reset autoSelectDone setiap kali affiliate param berubah
  const prevAffiliate = useRef<string | null>(null)
  useEffect(() => {
    const affiliateName = searchParams.get('affiliate')
    if (affiliateName !== prevAffiliate.current) {
      autoSelectDone.current = false
      prevAffiliate.current = affiliateName
    }
    if (!affiliateName || autoSelectDone.current || conversations.length === 0) return
    const match = conversations.find(c =>
      c.affiliate_name.toLowerCase() === affiliateName.toLowerCase()
    )
    if (match) {
      setSelected(match)
      autoSelectDone.current = true
    }
  }, [conversations, searchParams])

  // Tutup popup dengan Escape
  useEffect(() => {
    function handleEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') setShowTemplates(false)
    }
    if (showTemplates) {
      document.addEventListener('keydown', handleEsc)
      return () => document.removeEventListener('keydown', handleEsc)
    }
  }, [showTemplates])

  useEffect(() => {
    if (selected) loadMessages(selected.affiliate_id)
  }, [selected])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function loadConversations(q = '') {
    setLoadingConvs(true)
    try {
      const { data } = await apiClient.get(`/messages/conversations${q ? `?search=${encodeURIComponent(q)}` : ''}`)
      setConversations(Array.isArray(data) ? data : [])
    } catch { setConversations([]) }
    finally { setLoadingConvs(false) }
  }

  async function loadMessages(affiliateId: string) {
    try {
      const { data } = await apiClient.get(`/messages/history/${affiliateId}`)
      setMessages(Array.isArray(data) ? data : [])
    } catch { setMessages([]) }
  }

  async function loadWaNumbers() {
    try {
      const { data } = await apiClient.get('/messages/wa-numbers')
      setWaNumbers(Array.isArray(data) ? data : [])
    } catch { setWaNumbers([]) }
  }

  async function loadTemplates() {
    try {
      const { data } = await apiClient.get('/templates')
      setTemplates(Array.isArray(data) ? data : [])
    } catch { setTemplates([]) }
  }

  async function handleSend() {
    if (!newMsg.trim() || !selected) return
    setSending(true)
    try {
      await apiClient.post('/messages/send', {
        affiliate_id: selected.affiliate_id,
        message_content: newMsg.trim(),
      })
      setNewMsg('')
      await loadMessages(selected.affiliate_id)
      await loadConversations(search)
    } catch {} finally { setSending(false) }
  }

  async function handleUpdateWaNumber(id: string, phone: string, name: string) {
    try {
      await apiClient.put(`/messages/wa-numbers/${id}`, { phone_number: phone, display_name: name })
      await loadWaNumbers()
    } catch {}
  }

  function applyTemplate(tmpl: MessageTemplate) {
    // Substitusi variabel default
    let content = tmpl.content
    Object.entries(tmpl.default_values).forEach(([key, val]) => {
      content = content.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), val)
    })
    // Ganti nama affiliate jika ada
    if (selected) {
      content = content.replace(/\{\{nama_influencer\}\}/g, selected.affiliate_name)
    }
    setNewMsg(content)
    setShowTemplates(false)
  }

  // Filter template berdasarkan kategori WA affiliate yang dipilih
  const relevantTemplates = templates.filter(t =>
    !t.wa_category || t.wa_category === selected?.wa_category
  )

  async function handleBlastPreview() {
    setBlastLoading(true)
    try {
      const { data } = await apiClient.post('/messages/blast/preview', {
        wa_category: blastCategory || null,
      })
      setBlastPreview(Array.isArray(data) ? data : [])
      setBlastStep('preview')
    } catch { setBlastPreview([]) }
    finally { setBlastLoading(false) }
  }

  async function handleBlastSend() {
    if (!blastMessage.trim()) return
    setBlastLoading(true)
    try {
      const { data } = await apiClient.post('/messages/blast/send', {
        wa_category: blastCategory || null,
        message_content: blastMessage.trim(),
        template_id: blastTemplateId,
      })
      setBlastResult(data)
      setBlastStep('result')
      // Refresh conversations
      await loadConversations(search)
    } catch {} finally { setBlastLoading(false) }
  }

  function resetBlast() {
    setBlastStep('compose')
    setBlastPreview(null)
    setBlastResult(null)
    setBlastMessage('')
    setBlastCategory('')
    setBlastTemplateId(null)
  }

  const filtered = conversations.filter(c =>
    !search || c.affiliate_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex h-full">
      {/* ── Sidebar Conversations ── */}
      <div className="w-80 shrink-0 border-r border-[#1f1f1f] bg-[#0d0d0d] flex flex-col">
        <div className="p-4 border-b border-[#1f1f1f]">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-sm font-semibold text-white">History Pesan</h1>
            <div className="flex items-center gap-1">
              <button onClick={() => { setShowBlast(true); resetBlast() }}
                title="Kirim Massal"
                className="text-gray-500 hover:text-violet-400 transition-colors p-1">
                <Zap className="h-4 w-4" />
              </button>
              <button onClick={() => setShowWaSettings(!showWaSettings)}
                className="text-gray-500 hover:text-white transition-colors p-1">
                <Settings className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
            <input value={search} onChange={e => { setSearch(e.target.value); loadConversations(e.target.value) }}
              placeholder="Cari affiliate..."
              className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] pl-8 pr-3 py-2 text-xs text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loadingConvs ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-[#111111]" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center">
              <MessageCircle className="h-8 w-8 text-gray-700 mx-auto mb-2" />
              <p className="text-xs text-gray-600">Belum ada percakapan</p>
            </div>
          ) : (
            filtered.map(conv => (
              <button key={conv.affiliate_id} onClick={() => setSelected(conv)}
                className={`w-full text-left px-4 py-3 border-b border-[#1f1f1f] hover:bg-[#111111] transition-colors ${selected?.affiliate_id === conv.affiliate_id ? 'bg-[#111111] border-l-2 border-l-violet-500' : ''}`}>
                <div className="flex items-start gap-3">
                  <div className="h-9 w-9 rounded-full bg-violet-600/20 flex items-center justify-center text-xs font-bold text-violet-400 shrink-0">
                    {conv.affiliate_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-white truncate">{conv.affiliate_name}</span>
                      <span className="text-xs text-gray-600 shrink-0 ml-1">{formatTime(conv.last_message_at)}</span>
                    </div>
                    <p className="text-xs text-gray-500 truncate mt-0.5">{conv.last_message}</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      {conv.wa_category && (
                        <span className={`text-xs rounded-full px-1.5 py-0.5 ${CATEGORY_COLORS[conv.wa_category] ?? 'bg-gray-700/20 text-gray-400'}`}>
                          {conv.wa_category}
                        </span>
                      )}
                      {conv.unread_count > 0 && (
                        <span className="ml-auto bg-violet-600 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── Chat Area ── */}
      {selected ? (
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-3 border-b border-[#1f1f1f] bg-[#111111]">
            <div className="h-9 w-9 rounded-full bg-violet-600/20 flex items-center justify-center text-sm font-bold text-violet-400">
              {selected.affiliate_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-semibold text-white">{selected.affiliate_name}</p>
              <div className="flex items-center gap-2">
                {selected.wa_category && (
                  <span className={`text-xs rounded-full px-1.5 py-0.5 ${CATEGORY_COLORS[selected.wa_category] ?? 'bg-gray-700/20 text-gray-400'}`}>
                    {selected.wa_category}
                  </span>
                )}
                <span className="text-xs text-gray-500">{selected.message_count} pesan</span>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 ? (
              <div className="text-center py-12 text-gray-600 text-sm">Belum ada pesan</div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[70%] rounded-xl px-3 py-2 ${msg.direction === 'outbound' ? 'bg-violet-600 text-white' : 'bg-[#1a1a1a] text-gray-200'}`}>
                    <p className="text-sm">{msg.message_content}</p>
                    <div className={`flex items-center gap-1.5 mt-1 ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}>
                      <span className="text-xs opacity-60">{formatTime(msg.sent_at)}</span>
                      {msg.from_number && (
                        <span className="text-xs opacity-50">· {msg.from_number}</span>
                      )}
                      {msg.direction === 'outbound' && (
                        <span className="text-xs opacity-60">
                          {msg.status === 'read' ? '✓✓' : msg.status === 'delivered' ? '✓✓' : '✓'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-[#1f1f1f] bg-[#0d0d0d]">
            <div className="flex items-center gap-2">
              <button onClick={() => setShowTemplates(!showTemplates)}
                title="Pilih template"
                className={`rounded-lg p-2 transition-colors ${showTemplates ? 'bg-violet-600/20 text-violet-400' : 'text-gray-500 hover:text-white hover:bg-[#1a1a1a]'}`}>
                <FileText className="h-4 w-4" />
              </button>
              <input value={newMsg} onChange={e => setNewMsg(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Ketik pesan atau pilih template..."
                className="flex-1 rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none" />
              <button onClick={handleSend} disabled={sending || !newMsg.trim()}
                className="rounded-lg bg-violet-600 p-2 text-white hover:bg-violet-700 disabled:opacity-40 transition-colors">
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <MessageCircle className="h-12 w-12 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500">Pilih percakapan untuk melihat history pesan</p>
          </div>
        </div>
      )}

      {/* ── Template Panel (kolom ketiga) ── */}
      {showTemplates && selected && (
        <div className="w-64 shrink-0 border-l border-[#1f1f1f] bg-[#0d0d0d] flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#1f1f1f] shrink-0">
            <div>
              <p className="text-xs font-semibold text-white">Template Pesan</p>
              {selected.wa_category && (
                <p className="text-xs text-gray-500 mt-0.5">{selected.wa_category}</p>
              )}
            </div>
            <button onClick={() => setShowTemplates(false)}
              className="text-gray-500 hover:text-white transition-colors p-1">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {relevantTemplates.length === 0 ? (
              <div className="p-4 text-center">
                <p className="text-xs text-gray-600">Tidak ada template untuk kategori ini</p>
              </div>
            ) : relevantTemplates.map(tmpl => (
              <button key={tmpl.id} type="button" onClick={() => applyTemplate(tmpl)}
                className="w-full text-left px-4 py-3 hover:bg-[#111111] transition-colors border-b border-[#1f1f1f] last:border-0">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-medium text-white leading-tight">{tmpl.name}</span>
                  {tmpl.wa_category && (
                    <span className={`text-xs rounded-full px-1.5 py-0.5 shrink-0 ${CATEGORY_COLORS[tmpl.wa_category] ?? 'bg-gray-700/20 text-gray-400'}`}>
                      {tmpl.wa_category}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-600 mt-1 line-clamp-2">{tmpl.content}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Blast Modal ── */}
      {showBlast && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-xl border border-[#1f1f1f] bg-[#111111] shadow-2xl flex flex-col" style={{maxHeight: '85vh'}}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f1f1f] shrink-0">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-violet-400" />
                <span className="text-sm font-semibold text-white">Kirim Pesan Massal</span>
              </div>
              <button onClick={() => setShowBlast(false)} className="text-gray-500 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {blastStep === 'compose' && (
                <>
                  {/* Filter Kategori */}
                  <div>
                    <label className="text-xs font-medium text-gray-400 mb-2 block">Filter Kategori WA</label>
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        { value: '', label: 'Semua Kategori' },
                        { value: 'FnB', label: 'Makanan & Minuman' },
                        { value: 'Fashion', label: 'Fashion' },
                        { value: 'Kecantikan', label: 'Kecantikan' },
                        { value: 'Elektronik', label: 'Elektronik' },
                        { value: 'Olahraga', label: 'Olahraga' },
                        { value: 'Umum', label: 'Umum' },
                      ].map(cat => (
                        <button key={cat.value} type="button" onClick={() => setBlastCategory(cat.value)}
                          className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                            blastCategory === cat.value
                              ? 'bg-violet-600 text-white border-violet-600'
                              : 'border-[#2f2f2f] text-gray-400 hover:text-white'
                          }`}>
                          {cat.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Pilih Template (opsional) */}
                  <div>
                    <label className="text-xs font-medium text-gray-400 mb-2 block">
                      Template Pesan <span className="text-gray-600 font-normal">(opsional)</span>
                    </label>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {templates
                        .filter(t => !blastCategory || !t.wa_category || t.wa_category === blastCategory)
                        .map(t => (
                          <button key={t.id} type="button"
                            onClick={() => {
                              setBlastTemplateId(t.id)
                              let content = t.content
                              Object.entries(t.default_values).forEach(([k, v]) => {
                                content = content.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), v)
                              })
                              setBlastMessage(content)
                            }}
                            className={`w-full text-left px-3 py-2 rounded-lg text-xs border transition-colors ${
                              blastTemplateId === t.id
                                ? 'border-violet-500/60 bg-violet-500/10 text-violet-300'
                                : 'border-[#1f1f1f] text-gray-400 hover:border-[#2f2f2f]'
                            }`}>
                            <span className="font-medium">{t.name}</span>
                            {t.wa_category && (
                              <span className={`ml-2 rounded-full px-1.5 py-0.5 ${CATEGORY_COLORS[t.wa_category] ?? 'bg-gray-700/20 text-gray-500'}`}>
                                {t.wa_category}
                              </span>
                            )}
                          </button>
                        ))}
                    </div>
                  </div>

                  {/* Isi Pesan */}
                  <div>
                    <label className="text-xs font-medium text-gray-400 mb-1 block">Isi Pesan</label>
                    <textarea value={blastMessage} onChange={e => setBlastMessage(e.target.value)}
                      rows={5} placeholder="Ketik pesan yang akan dikirim ke semua affiliate..."
                      className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none resize-none" />
                  </div>

                  <button onClick={handleBlastPreview} disabled={!blastMessage.trim() || blastLoading}
                    className="w-full rounded-lg bg-violet-600 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40 flex items-center justify-center gap-2">
                    {blastLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Users className="h-4 w-4" />}
                    Preview Penerima
                  </button>
                </>
              )}

              {blastStep === 'preview' && blastPreview && (
                <>
                  <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-3">
                    <p className="text-xs text-gray-400 mb-1">Pesan yang akan dikirim:</p>
                    <p className="text-sm text-white whitespace-pre-wrap">{blastMessage}</p>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-medium text-gray-400">Penerima ({blastPreview.length} affiliate)</p>
                      <button onClick={() => setBlastStep('compose')} className="text-xs text-violet-400 hover:text-violet-300">
                        Ubah
                      </button>
                    </div>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {blastPreview.map(r => (
                        <div key={r.affiliate_id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#0a0a0a] border border-[#1f1f1f]">
                          <div className="flex items-center gap-2">
                            <div className="h-6 w-6 rounded-full bg-violet-600/20 flex items-center justify-center text-xs font-bold text-violet-400 shrink-0">
                              {r.affiliate_name.charAt(0)}
                            </div>
                            <span className="text-xs text-white">{r.affiliate_name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs rounded-full px-1.5 py-0.5 ${CATEGORY_COLORS[r.wa_category] ?? 'bg-gray-700/20 text-gray-400'}`}>
                              {r.wa_category}
                            </span>
                            <span className="text-xs text-gray-600 font-mono">{r.phone_number}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {blastPreview.length === 0 ? (
                    <p className="text-center text-sm text-gray-500 py-4">Tidak ada affiliate yang cocok dengan filter ini</p>
                  ) : (
                    <button onClick={handleBlastSend} disabled={blastLoading}
                      className="w-full rounded-lg bg-violet-600 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40 flex items-center justify-center gap-2">
                      {blastLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                      Kirim ke {blastPreview.length} Affiliate
                    </button>
                  )}
                </>
              )}

              {blastStep === 'result' && blastResult && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg bg-green-900/20 border border-green-900/30 p-3 text-center">
                      <CheckCircle className="h-5 w-5 text-green-400 mx-auto mb-1" />
                      <p className="text-lg font-bold text-green-400">{blastResult.sent}</p>
                      <p className="text-xs text-gray-500">Terkirim</p>
                    </div>
                    <div className="rounded-lg bg-red-900/20 border border-red-900/30 p-3 text-center">
                      <AlertCircle className="h-5 w-5 text-red-400 mx-auto mb-1" />
                      <p className="text-lg font-bold text-red-400">{blastResult.failed}</p>
                      <p className="text-xs text-gray-500">Gagal</p>
                    </div>
                    <div className="rounded-lg bg-gray-800/20 border border-gray-700/30 p-3 text-center">
                      <Users className="h-5 w-5 text-gray-400 mx-auto mb-1" />
                      <p className="text-lg font-bold text-gray-400">{blastResult.total}</p>
                      <p className="text-xs text-gray-500">Total</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 text-center">
                    Pesan massal selesai dikirim. History tersimpan di setiap percakapan.
                  </p>
                  <button onClick={() => { setShowBlast(false); resetBlast() }}
                    className="w-full rounded-lg bg-[#1a1a1a] py-2.5 text-sm text-gray-300 hover:text-white border border-[#2f2f2f]">
                    Tutup
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── WA Numbers Settings Panel ── */}
      {showWaSettings && (
        <div className="w-72 shrink-0 border-l border-[#1f1f1f] bg-[#0d0d0d] flex flex-col">
          <div className="p-4 border-b border-[#1f1f1f]">
            <h2 className="text-sm font-semibold text-white">Nomor WhatsApp per Kategori</h2>
            <p className="text-xs text-gray-500 mt-0.5">Sistem otomatis pilih nomor berdasarkan kategori affiliate</p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {waNumbers.map(wa => (
              <WaNumberCard key={wa.id} wa={wa} onUpdate={handleUpdateWaNumber} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function WaNumberCard({ wa, onUpdate }: { wa: WaNumber; onUpdate: (id: string, phone: string, name: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [phone, setPhone] = useState(wa.phone_number)
  const [name, setName] = useState(wa.display_name || '')

  return (
    <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-3">
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs rounded-full px-2 py-0.5 ${CATEGORY_COLORS[wa.category] ?? 'bg-gray-700/20 text-gray-400'}`}>
          {wa.category}
        </span>
        <button onClick={() => setEditing(!editing)} className="text-xs text-violet-400 hover:text-violet-300">
          {editing ? 'Batal' : 'Edit'}
        </button>
      </div>
      {editing ? (
        <div className="space-y-2">
          <input value={phone} onChange={e => setPhone(e.target.value)}
            placeholder="Nomor WA (+628...)"
            className="w-full rounded border border-[#2f2f2f] bg-[#0d0d0d] px-2 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none" />
          <input value={name} onChange={e => setName(e.target.value)}
            placeholder="Nama tampilan"
            className="w-full rounded border border-[#2f2f2f] bg-[#0d0d0d] px-2 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none" />
          <button onClick={() => { onUpdate(wa.id, phone, name); setEditing(false) }}
            className="w-full rounded bg-violet-600 py-1.5 text-xs text-white hover:bg-violet-700">
            Simpan
          </button>
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-1.5">
            <Phone className="h-3 w-3 text-green-400" />
            <span className="text-xs text-white font-mono">{wa.phone_number}</span>
          </div>
          {wa.display_name && <p className="text-xs text-gray-500 mt-0.5">{wa.display_name}</p>}
        </div>
      )}
    </div>
  )
}
