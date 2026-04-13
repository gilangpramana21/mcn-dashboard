'use client'
import { useState, useEffect } from 'react'
import { Bot, Play, Settings, CheckCircle, AlertCircle, Loader2, Key, RefreshCw, Users, MessageCircle, ExternalLink } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

interface TokenStatus {
  status: 'valid' | 'expired' | 'no_token'
  expires_at: string | null
  shop_id: string | null
  shop_name: string | null
  has_token: boolean
  has_cipher: boolean
}

interface AgentResult {
  found: number
  new_saved: number
  already_exists: number
  messages_sent: number
  errors: string[]
  creators: any[]
}

interface AgentHistory {
  total: number
  messages: {
    name: string
    tiktok_id: string
    message: string
    status: string
    sent_at: string
    has_whatsapp: boolean
    followers: number
  }[]
}

const CATEGORIES = [
  'Kecantikan & Perawatan', 'Fashion Wanita', 'Fashion Pria',
  'Makanan & Minuman', 'Skincare', 'Elektronik & Gadget',
  'Olahraga & Outdoor', 'Kesehatan & Suplemen', 'Gaming',
]

export default function AgentPage() {
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null)
  const [loadingToken, setLoadingToken] = useState(true)
  const [activeTab, setActiveTab] = useState<'run' | 'token' | 'history' | 'data'>('run')

  // Agent config
  const [keyword, setKeyword] = useState('')
  const [minFollowers, setMinFollowers] = useState(1000)
  const [maxFollowers, setMaxFollowers] = useState(0)
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [maxCreators, setMaxCreators] = useState(50)
  const [autoSend, setAutoSend] = useState(true)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<AgentResult | null>(null)

  // Token manual
  const [manualToken, setManualToken] = useState('')
  const [manualRefresh, setManualRefresh] = useState('')
  const [manualCipher, setManualCipher] = useState('')
  const [savingToken, setSavingToken] = useState(false)
  const [tokenSaved, setTokenSaved] = useState(false)
  const [fetchingCipher, setFetchingCipher] = useState(false)

  // History
  const [history, setHistory] = useState<AgentHistory | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [fetchData, setFetchData] = useState<any>(null)
  const [loadingFetch, setLoadingFetch] = useState(false)

  useEffect(() => {
    loadTokenStatus()
  }, [])

  useEffect(() => {
    if (activeTab === 'history') loadHistory()
    if (activeTab === 'data') loadFetchData()
  }, [activeTab])

  async function loadTokenStatus() {
    setLoadingToken(true)
    try {
      const { data } = await apiClient.get('/tiktok-shop/token/status')
      setTokenStatus(data)
    } catch {
      setTokenStatus({ status: 'no_token', expires_at: null, shop_id: null, shop_name: null, has_token: false, has_cipher: false })
    } finally {
      setLoadingToken(false)
    }
  }

  async function handleSaveToken() {
    if (!manualToken.trim()) return
    setSavingToken(true)
    try {
      await apiClient.post('/tiktok-shop/token/manual', {
        access_token: manualToken.trim(),
        refresh_token: manualRefresh.trim(),
        expires_in: 86400,
        shop_cipher: manualCipher.trim() || undefined,
      })
      setTokenSaved(true)
      await loadTokenStatus()
      setTimeout(() => setTokenSaved(false), 2000)
    } catch {} finally { setSavingToken(false) }
  }

  async function handleFetchCipher() {
    setFetchingCipher(true)
    try {
      await apiClient.post('/tiktok-shop/token/fetch-cipher')
      await loadTokenStatus()
    } catch {} finally { setFetchingCipher(false) }
  }

  async function handleRunAgent() {
    setRunning(true)
    setResult(null)
    try {
      const { data } = await apiClient.post('/tiktok-shop/agent/run', {
        keyword,
        min_followers: minFollowers,
        max_followers: maxFollowers || 0,
        categories: selectedCategories,
        max_creators: maxCreators,
        auto_send_message: autoSend,
      })
      setResult(data)
    } catch (e: any) {
      setResult({
        found: 0, new_saved: 0, already_exists: 0, messages_sent: 0,
        errors: [e?.response?.data?.detail ?? 'Gagal menjalankan agent'],
        creators: [],
      })
    } finally { setRunning(false) }
  }

  async function loadHistory() {
    setLoadingHistory(true)
    try {
      const { data } = await apiClient.get('/tiktok-shop/agent/history')
      setHistory(data)
    } catch {} finally { setLoadingHistory(false) }
  }

  async function loadFetchData() {
    setLoadingFetch(true)
    try {
      const { data } = await apiClient.get('/tiktok-shop/data/fetch')
      setFetchData(data)
    } catch (e: any) {
      setFetchData({ error: e?.response?.data?.detail ?? 'Gagal ambil data' })
    } finally { setLoadingFetch(false) }
  }

  function toggleCategory(cat: string) {
    setSelectedCategories(prev =>
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    )
  }

  const tokenOk = tokenStatus?.status === 'valid'

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-violet-600/20 flex items-center justify-center">
          <Bot className="h-5 w-5 text-violet-400" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-white">TikTok Shop Agent</h1>
          <p className="text-sm text-gray-500">Otomatis cari affiliator, kirim pesan, simpan ke database</p>
        </div>
        <div className="ml-auto">
          {loadingToken ? (
            <div className="h-6 w-24 animate-pulse rounded-full bg-[#1a1a1a]" />
          ) : tokenOk ? (
            <span className="flex items-center gap-1.5 rounded-full bg-green-900/20 border border-green-900/30 px-3 py-1 text-xs text-green-400">
              <div className="h-1.5 w-1.5 rounded-full bg-green-400" /> Token Aktif
            </span>
          ) : (
            <span className="flex items-center gap-1.5 rounded-full bg-red-900/20 border border-red-900/30 px-3 py-1 text-xs text-red-400">
              <div className="h-1.5 w-1.5 rounded-full bg-red-400" /> Perlu Token
            </span>
          )}
        </div>
      </div>

      {/* Alur kerja */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { step: '1', label: 'Authorize', desc: 'Hubungkan akun Seller Center', icon: '🔑' },
          { step: '2', label: 'Cari Creator', desc: 'Agent search di marketplace', icon: '🔍' },
          { step: '3', label: 'Simpan DB', desc: 'Data tersimpan otomatis', icon: '💾' },
          { step: '4', label: 'Kirim Pesan', desc: 'Chat TikTok minta nomor WA', icon: '💬' },
        ].map(s => (
          <div key={s.step} className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="h-5 w-5 rounded-full bg-violet-600/20 text-violet-400 text-xs flex items-center justify-center font-bold">{s.step}</span>
              <span className="text-base">{s.icon}</span>
            </div>
            <p className="text-xs font-medium text-white">{s.label}</p>
            <p className="text-xs text-gray-600 mt-0.5">{s.desc}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-[#1f1f1f] bg-[#0d0d0d] p-1 w-fit">
        {[
          { id: 'run', label: 'Jalankan Agent', icon: Play },
          { id: 'token', label: 'Pengaturan Token', icon: Key },
          { id: 'history', label: 'Riwayat', icon: MessageCircle },
          { id: 'data', label: 'Ambil Data', icon: RefreshCw },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors ${
              activeTab === tab.id ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'
            }`}>
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: Jalankan Agent */}
      {activeTab === 'run' && (
        <div className="space-y-5">
          {!tokenOk && (
            <div className="rounded-xl border border-yellow-900/30 bg-yellow-900/10 p-4 flex items-start gap-3">
              <AlertCircle className="h-4 w-4 text-yellow-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-yellow-300">Token belum dikonfigurasi</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Pergi ke tab "Pengaturan Token" untuk input access token TikTok Shop kamu.
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Keyword Pencarian</label>
              <input value={keyword} onChange={e => setKeyword(e.target.value)}
                placeholder="cth: skincare, fashion, kuliner..."
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Maks. Creator per Run</label>
              <input type="number" value={maxCreators} onChange={e => setMaxCreators(Number(e.target.value))}
                min={1} max={200}
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Min. Followers</label>
              <input type="number" value={minFollowers} onChange={e => setMinFollowers(Number(e.target.value))}
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Maks. Followers <span className="text-gray-600">(0 = tidak dibatasi)</span></label>
              <input type="number" value={maxFollowers} onChange={e => setMaxFollowers(Number(e.target.value))}
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none" />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-400 mb-2 block">Filter Kategori</label>
            <div className="flex flex-wrap gap-1.5">
              {CATEGORIES.map(cat => (
                <button key={cat} onClick={() => toggleCategory(cat)}
                  className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                    selectedCategories.includes(cat)
                      ? 'bg-violet-600 text-white border-violet-600'
                      : 'border-[#2f2f2f] text-gray-400 hover:text-white'
                  }`}>
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <button onClick={() => setAutoSend(!autoSend)}
              className={`h-5 w-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                autoSend ? 'bg-violet-600 border-violet-600' : 'border-[#3f3f3f]'
              }`}>
              {autoSend && <CheckCircle className="h-3 w-3 text-white" />}
            </button>
            <div>
              <p className="text-sm font-medium text-white">Auto-kirim pesan TikTok Chat</p>
              <p className="text-xs text-gray-500">Setelah creator ditemukan, langsung kirim pesan minta nomor WA via TikTok chat</p>
            </div>
          </div>

          <button onClick={handleRunAgent} disabled={running || !tokenOk}
            className="w-full rounded-lg bg-violet-600 py-3 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40 flex items-center justify-center gap-2">
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {running ? 'Agent sedang berjalan...' : 'Jalankan Agent'}
          </button>

          {/* Result */}
          {result && (
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-3">
                <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-3 text-center">
                  <p className="text-xl font-bold text-white">{result.found}</p>
                  <p className="text-xs text-gray-500">Ditemukan</p>
                </div>
                <div className="rounded-xl border border-green-900/30 bg-green-900/10 p-3 text-center">
                  <p className="text-xl font-bold text-green-400">{result.new_saved}</p>
                  <p className="text-xs text-gray-500">Disimpan baru</p>
                </div>
                <div className="rounded-xl border border-blue-900/30 bg-blue-900/10 p-3 text-center">
                  <p className="text-xl font-bold text-blue-400">{result.messages_sent}</p>
                  <p className="text-xs text-gray-500">Pesan terkirim</p>
                </div>
                <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-3 text-center">
                  <p className="text-xl font-bold text-gray-400">{result.already_exists}</p>
                  <p className="text-xs text-gray-500">Sudah ada</p>
                </div>
              </div>

              {result.errors.length > 0 && (
                <div className="rounded-xl border border-red-900/30 bg-red-900/10 p-3">
                  <p className="text-xs font-medium text-red-400 mb-1">Error ({result.errors.length}):</p>
                  {result.errors.map((e, i) => <p key={i} className="text-xs text-red-300">{e}</p>)}
                </div>
              )}

              {result.creators.length > 0 && (
                <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
                  <div className="px-4 py-2 bg-[#0d0d0d] border-b border-[#1f1f1f]">
                    <p className="text-xs text-gray-400">Creator yang diproses</p>
                  </div>
                  <div className="divide-y divide-[#1f1f1f] max-h-48 overflow-y-auto">
                    {result.creators.map((c, i) => (
                      <div key={i} className="flex items-center justify-between px-4 py-2">
                        <span className="text-xs text-white">{c.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">{c.followers?.toLocaleString()} followers</span>
                          {c.message_sent && <span className="text-xs text-blue-400">💬 Terkirim</span>}
                          {c.is_new && <span className="text-xs text-green-400">✓ Baru</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab: Token */}
      {activeTab === 'token' && (
        <div className="space-y-5">
          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 space-y-3">
            <p className="text-sm font-medium text-white">Status Token Saat Ini</p>
            {loadingToken ? (
              <div className="h-8 animate-pulse rounded bg-[#1a1a1a]" />
            ) : tokenOk ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircle className="h-4 w-4" />
                  <span className="text-sm">Token aktif</span>
                  {tokenStatus?.expires_at && (
                    <span className="text-xs text-gray-500">· Expires: {new Date(tokenStatus.expires_at).toLocaleString('id-ID')}</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {tokenStatus?.has_cipher ? (
                    <span className="flex items-center gap-1.5 text-xs text-green-400">
                      <CheckCircle className="h-3 w-3" /> Shop Cipher tersimpan
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-xs text-yellow-400">
                      <AlertCircle className="h-3 w-3" /> Shop Cipher belum ada
                    </span>
                  )}
                  <button onClick={handleFetchCipher} disabled={fetchingCipher}
                    className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300 disabled:opacity-40">
                    {fetchingCipher ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                    Auto-fetch Cipher
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm">{tokenStatus?.status === 'expired' ? 'Token expired' : 'Belum ada token'}</span>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 space-y-4">
            <div>
              <p className="text-sm font-medium text-white mb-1">Cara 1 — OAuth (Otomatis)</p>
              <p className="text-xs text-gray-500 mb-3">
                Klik tombol di bawah, login dengan akun TikTok Seller Center kamu, lalu authorize. Token akan tersimpan otomatis.
              </p>
              <button
                onClick={async () => {
                  try {
                    const redirect = `${window.location.origin}/oauth/tiktok/callback`
                    const { data } = await apiClient.get(`/tiktok-shop/auth-url?redirect_uri=${encodeURIComponent(redirect)}`)
                    window.open(data.auth_url, '_blank', 'width=600,height=700')
                  } catch {}
                }}
                className="flex items-center gap-2 rounded-lg bg-[#1a1a1a] border border-[#2f2f2f] px-4 py-2 text-sm text-white hover:border-violet-500/40 transition-colors">
                <ExternalLink className="h-4 w-4 text-violet-400" />
                Buka Halaman Authorize TikTok
              </button>
            </div>
            <div className="border-t border-[#1f1f1f] pt-4">
              <p className="text-sm font-medium text-white mb-1">Cara 2 — Input Token Manual</p>
              <p className="text-xs text-gray-500 mb-3">
                Dapatkan access token dari TikTok Shop Partner Center, lalu paste di sini.
              </p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Access Token</label>
              <input value={manualToken} onChange={e => setManualToken(e.target.value)}
                placeholder="Paste access token di sini..."
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white font-mono focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Refresh Token <span className="text-gray-600">(opsional)</span></label>
              <input value={manualRefresh} onChange={e => setManualRefresh(e.target.value)}
                placeholder="Refresh token untuk perpanjang otomatis..."
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white font-mono focus:border-violet-500 focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1 block">Shop Cipher <span className="text-gray-600">(opsional — bisa auto-fetch setelah simpan)</span></label>
              <input value={manualCipher} onChange={e => setManualCipher(e.target.value)}
                placeholder="Shop cipher dari authorized shops..."
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white font-mono focus:border-violet-500 focus:outline-none" />
            </div>
            <button onClick={handleSaveToken} disabled={savingToken || !manualToken.trim()}
              className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-40 flex items-center gap-2">
              {savingToken ? <Loader2 className="h-4 w-4 animate-spin" /> : tokenSaved ? <CheckCircle className="h-4 w-4" /> : <Key className="h-4 w-4" />}
              {tokenSaved ? 'Tersimpan!' : 'Simpan Token'}
            </button>
          </div>

          <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-4">
            <p className="text-xs font-medium text-gray-400 mb-2">Cara mendapatkan Access Token (manual):</p>
            <ol className="space-y-1.5 text-xs text-gray-500">
              <li>1. Buka <span className="text-violet-400">partner.tiktokshop.com</span> → login</li>
              <li>2. Klik nama app kamu → tab <span className="text-white">Sandbox</span> atau <span className="text-white">Testing</span></li>
              <li>3. Cari tombol <span className="text-white">"Generate Access Token"</span> atau <span className="text-white">"Get Token"</span></li>
              <li>4. Pilih shop yang ingin dihubungkan → copy token</li>
              <li>5. Paste di form di atas</li>
            </ol>
            <p className="text-xs text-yellow-400 mt-3">
              Catatan: Jika tidak ada menu token di Partner Center, kemungkinan app perlu di-review dulu oleh TikTok. Gunakan Cara 1 (OAuth) sebagai alternatif.
            </p>
          </div>
        </div>
      )}

      {/* Tab: History */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">{history?.total ?? 0} pesan terkirim via TikTok Chat</p>
            <button onClick={loadHistory} className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
              <RefreshCw className="h-3 w-3" /> Refresh
            </button>
          </div>

          {loadingHistory ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 animate-pulse rounded-xl bg-[#111111]" />)}
            </div>
          ) : !history?.messages.length ? (
            <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-12 text-center">
              <MessageCircle className="h-8 w-8 text-gray-700 mx-auto mb-2" />
              <p className="text-sm text-gray-500">Belum ada riwayat pesan agent</p>
            </div>
          ) : (
            <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#1f1f1f] bg-[#0d0d0d]">
                    <th className="px-4 py-2.5 text-left text-gray-500">Creator</th>
                    <th className="px-4 py-2.5 text-right text-gray-500">Followers</th>
                    <th className="px-4 py-2.5 text-center text-gray-500">WA</th>
                    <th className="px-4 py-2.5 text-center text-gray-500">Status</th>
                    <th className="px-4 py-2.5 text-right text-gray-500">Waktu</th>
                  </tr>
                </thead>
                <tbody>
                  {history.messages.map((m, i) => (
                    <tr key={i} className="border-b border-[#1f1f1f] hover:bg-[#111111]">
                      <td className="px-4 py-2.5">
                        <p className="text-white font-medium">{m.name}</p>
                        <p className="text-gray-600">{m.tiktok_id}</p>
                      </td>
                      <td className="px-4 py-2.5 text-right text-gray-400">
                        {m.followers?.toLocaleString() ?? '—'}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        {m.has_whatsapp ? (
                          <span className="text-green-400">✓ Ada</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`rounded-full px-2 py-0.5 ${
                          m.status === 'sent' ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'
                        }`}>
                          {m.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right text-gray-500">
                        {m.sent_at ? new Date(m.sent_at).toLocaleString('id-ID', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      {/* Tab: Ambil Data */}
      {activeTab === 'data' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">Data langsung dari TikTok Shop API</p>
            <button onClick={loadFetchData} className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
              <RefreshCw className="h-3 w-3" /> Refresh
            </button>
          </div>

          {loadingFetch ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-[#111111]" />)}
            </div>
          ) : fetchData?.error ? (
            <div className="rounded-xl border border-red-900/30 bg-red-900/10 p-4">
              <p className="text-sm text-red-400">{fetchData.error}</p>
            </div>
          ) : fetchData ? (
            <div className="space-y-4">
              {/* Kolaborasi */}
              <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
                <div className="px-4 py-2.5 bg-[#0d0d0d] border-b border-[#1f1f1f] flex items-center justify-between">
                  <p className="text-xs font-medium text-white">Kolaborasi</p>
                  {fetchData.collaborations?.error ? (
                    <span className="text-xs text-red-400">{fetchData.collaborations.error}</span>
                  ) : (
                    <span className="text-xs text-gray-500">{fetchData.collaborations?.data?.length ?? 0} item</span>
                  )}
                </div>
                {!fetchData.collaborations?.error && fetchData.collaborations?.data?.length > 0 ? (
                  <div className="divide-y divide-[#1f1f1f] max-h-48 overflow-y-auto">
                    {fetchData.collaborations.data.map((c: any, i: number) => (
                      <div key={i} className="px-4 py-2.5 flex items-center justify-between">
                        <span className="text-xs text-white">{c.creator_name ?? c.name ?? `Kolaborasi #${i + 1}`}</span>
                        <span className="text-xs text-gray-500">{c.status ?? '—'}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="px-4 py-6 text-center text-xs text-gray-600">
                    {fetchData.collaborations?.error ?? 'Belum ada kolaborasi'}
                  </div>
                )}
              </div>

              {/* Produk */}
              <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
                <div className="px-4 py-2.5 bg-[#0d0d0d] border-b border-[#1f1f1f] flex items-center justify-between">
                  <p className="text-xs font-medium text-white">Produk Toko</p>
                  {fetchData.products?.error ? (
                    <span className="text-xs text-red-400">{fetchData.products.error}</span>
                  ) : (
                    <span className="text-xs text-gray-500">{fetchData.products?.data?.length ?? 0} item</span>
                  )}
                </div>
                {!fetchData.products?.error && fetchData.products?.data?.length > 0 ? (
                  <div className="divide-y divide-[#1f1f1f] max-h-48 overflow-y-auto">
                    {fetchData.products.data.map((p: any, i: number) => (
                      <div key={i} className="px-4 py-2.5 flex items-center justify-between">
                        <span className="text-xs text-white">{p.product_name ?? p.name ?? `Produk #${i + 1}`}</span>
                        <span className="text-xs text-gray-500">{p.status ?? '—'}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="px-4 py-6 text-center text-xs text-gray-600">
                    {fetchData.products?.error ?? 'Belum ada produk'}
                  </div>
                )}
              </div>

              {/* Creator yang pernah kolaborasi */}
              <div className="rounded-xl border border-[#1f1f1f] overflow-hidden">
                <div className="px-4 py-2.5 bg-[#0d0d0d] border-b border-[#1f1f1f] flex items-center justify-between">
                  <p className="text-xs font-medium text-white">Creator Kolaborasi</p>
                  {fetchData.creators?.error ? (
                    <span className="text-xs text-red-400">{fetchData.creators.error}</span>
                  ) : (
                    <span className="text-xs text-gray-500">{fetchData.creators?.data?.length ?? 0} item</span>
                  )}
                </div>
                {!fetchData.creators?.error && fetchData.creators?.data?.length > 0 ? (
                  <div className="divide-y divide-[#1f1f1f] max-h-48 overflow-y-auto">
                    {fetchData.creators.data.map((c: any, i: number) => (
                      <div key={i} className="px-4 py-2.5 flex items-center justify-between">
                        <span className="text-xs text-white">{c.creator_name ?? c.name ?? `Creator #${i + 1}`}</span>
                        <span className="text-xs text-gray-500">{c.follower_count?.toLocaleString() ?? '—'} followers</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="px-4 py-6 text-center text-xs text-gray-600">
                    {fetchData.creators?.error ?? 'Belum ada creator kolaborasi'}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-yellow-900/30 bg-yellow-900/10 p-3">
                <p className="text-xs text-yellow-400">
                  Catatan: Endpoint search creator tidak tersedia untuk Custom App. Data di atas adalah yang bisa diakses dengan scope "Creator collaborations".
                </p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-12 text-center">
              <RefreshCw className="h-8 w-8 text-gray-700 mx-auto mb-2" />
              <p className="text-sm text-gray-500">Klik Refresh untuk ambil data</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
