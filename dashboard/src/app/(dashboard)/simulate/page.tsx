'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import { Phone, Store, Send, Zap, Users, MessageCircle } from 'lucide-react'

interface Affiliate {
  id: string
  name: string
  tiktok_user_id: string | null
  phone_number: string | null
  has_whatsapp: boolean
}

const SAMPLE_MESSAGES_WA = [
  'Halo kak, saya tertarik dengan kolaborasi ini. Bisa ceritakan lebih lanjut?',
  'Nomor WA saya: 081298765432. Silakan hubungi saya ya kak!',
  'Oke kak, deal! Saya setuju dengan SOW-nya.',
  'Produknya sudah saya terima. Akan saya buat konten minggu ini!',
  'Kak, kapan sample dikirim? Saya sudah siap buat konten.',
]

const SAMPLE_MESSAGES_TIKTOK = [
  'Hai! Saya sudah lihat brief-nya. Kapan bisa mulai?',
  'Halo kak, saya mau tanya soal komisi produknya.',
  'Konten sudah saya upload, bisa dicek ya kak!',
  'Saya tertarik kolaborasi, bisa share link produknya?',
  'Kak, ada update soal campaign batch berikutnya?',
]

export default function SimulatePage() {
  const [selectedAffiliate, setSelectedAffiliate] = useState<Affiliate | null>(null)
  const [channel, setChannel] = useState<'whatsapp' | 'tiktok_seller'>('whatsapp')
  const [customMessage, setCustomMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [sentCount, setSentCount] = useState(0)

  const { data: affiliates = [] } = useQuery({
    queryKey: ['affiliates-simulate'],
    queryFn: () => apiClient.get('/inbox/affiliates-with-wa').then(r => (r as any).data ?? r),
    retry: false,
  })

  const affiliatesWithWA = (affiliates as Affiliate[]).filter(a => a.has_whatsapp)
  const affiliatesAll = affiliates as Affiliate[]

  async function sendSimulation(affiliateName: string, ch: string, message: string, fromNumber?: string) {
    setSending(true)
    try {
      await apiClient.post('/inbox/simulate', {
        affiliate_name: affiliateName,
        channel: ch,
        message_content: message,
        from_number: fromNumber || null,
      })
      setSentCount(c => c + 1)
      toast.success(`Pesan dari ${affiliateName} masuk!`, {
        description: `Via ${ch === 'whatsapp' ? 'WhatsApp' : 'TikTok Seller'} — lihat lonceng di atas`,
      })
    } catch {
      toast.error('Gagal mengirim simulasi')
    } finally {
      setSending(false)
    }
  }

  async function handleQuickSend(message: string) {
    if (!selectedAffiliate) {
      toast.warning('Pilih affiliator dulu')
      return
    }
    const fromNumber = channel === 'whatsapp'
      ? (selectedAffiliate.phone_number || '+6281234567890')
      : (selectedAffiliate.tiktok_user_id || '@affiliator')
    await sendSimulation(selectedAffiliate.name, channel, message, fromNumber)
  }

  async function handleCustomSend() {
    if (!selectedAffiliate || !customMessage.trim()) return
    const fromNumber = channel === 'whatsapp'
      ? (selectedAffiliate.phone_number || '+6281234567890')
      : (selectedAffiliate.tiktok_user_id || '@affiliator')
    await sendSimulation(selectedAffiliate.name, channel, customMessage.trim(), fromNumber)
    setCustomMessage('')
  }

  async function handleBulkSimulate() {
    // Kirim 3 pesan dari affiliator berbeda sekaligus
    const samples = [
      { name: 'Siti Rahayu', ch: 'whatsapp', msg: 'Halo kak, saya tertarik kolaborasi!', from: '+6281234567890' },
      { name: 'Budi Santoso', ch: 'tiktok_seller', msg: 'Hai! Sudah lihat brief-nya, kapan mulai?', from: '@budisantosofashion' },
      { name: 'Dewi Kusuma', ch: 'whatsapp', msg: 'Nomor WA saya: 081298765432', from: '+6281298765432' },
    ]
    for (const s of samples) {
      await sendSimulation(s.name, s.ch, s.msg, s.from)
      await new Promise(r => setTimeout(r, 300))
    }
  }

  const sampleMessages = channel === 'whatsapp' ? SAMPLE_MESSAGES_WA : SAMPLE_MESSAGES_TIKTOK

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-400" />
            Simulasi Pesan Masuk
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Test notifikasi pesan masuk dari affiliator via WhatsApp atau TikTok Seller Center
          </p>
        </div>
        {sentCount > 0 && (
          <div className="rounded-full bg-violet-600/20 border border-violet-600/30 px-3 py-1.5 text-xs text-violet-400">
            {sentCount} pesan terkirim hari ini
          </div>
        )}
      </div>

      {/* Step 1: Pilih Affiliator */}
      <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 space-y-4">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold text-white">1</div>
          <p className="text-sm font-semibold text-white">Pilih Affiliator</p>
          <span className="text-xs text-gray-500">({affiliatesAll.length} affiliator tersedia)</span>
        </div>

        <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-1">
          {affiliatesAll.length === 0 ? (
            <p className="text-xs text-gray-600 py-4 text-center">Belum ada affiliator di database</p>
          ) : (
            affiliatesAll.map(aff => (
              <button
                key={aff.id}
                onClick={() => setSelectedAffiliate(aff)}
                className={`flex items-center gap-3 rounded-lg border px-4 py-2.5 text-left transition-colors ${
                  selectedAffiliate?.id === aff.id
                    ? 'border-violet-500/60 bg-violet-950/30'
                    : 'border-[#2f2f2f] hover:border-[#3f3f3f]'
                }`}
              >
                <div className="h-8 w-8 rounded-full bg-violet-600/20 flex items-center justify-center text-xs font-bold text-violet-400 shrink-0">
                  {aff.name.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{aff.name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {aff.tiktok_user_id && (
                      <span className="text-xs text-gray-500">{aff.tiktok_user_id}</span>
                    )}
                    {aff.has_whatsapp && aff.phone_number && (
                      <span className="flex items-center gap-1 text-xs text-green-400">
                        <Phone className="h-3 w-3" /> {aff.phone_number}
                      </span>
                    )}
                    {!aff.has_whatsapp && (
                      <span className="text-xs text-gray-600">Belum ada WA</span>
                    )}
                  </div>
                </div>
                {selectedAffiliate?.id === aff.id && (
                  <div className="h-2 w-2 rounded-full bg-violet-500 shrink-0" />
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Step 2: Pilih Channel */}
      <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 space-y-3">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold text-white">2</div>
          <p className="text-sm font-semibold text-white">Pilih Channel</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setChannel('whatsapp')}
            className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
              channel === 'whatsapp' ? 'border-green-500/50 bg-green-950/20' : 'border-[#2f2f2f] hover:border-[#3f3f3f]'
            }`}
          >
            <Phone className={`h-5 w-5 ${channel === 'whatsapp' ? 'text-green-400' : 'text-gray-500'}`} />
            <div className="text-left">
              <p className={`text-sm font-medium ${channel === 'whatsapp' ? 'text-green-400' : 'text-gray-300'}`}>WhatsApp</p>
              {selectedAffiliate?.phone_number ? (
                <p className="text-xs text-gray-500">{selectedAffiliate.phone_number}</p>
              ) : (
                <p className="text-xs text-gray-600">Nomor dummy</p>
              )}
            </div>
          </button>
          <button
            onClick={() => setChannel('tiktok_seller')}
            className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
              channel === 'tiktok_seller' ? 'border-pink-500/50 bg-pink-950/20' : 'border-[#2f2f2f] hover:border-[#3f3f3f]'
            }`}
          >
            <Store className={`h-5 w-5 ${channel === 'tiktok_seller' ? 'text-pink-400' : 'text-gray-500'}`} />
            <div className="text-left">
              <p className={`text-sm font-medium ${channel === 'tiktok_seller' ? 'text-pink-400' : 'text-gray-300'}`}>TikTok Seller</p>
              {selectedAffiliate?.tiktok_user_id ? (
                <p className="text-xs text-gray-500">{selectedAffiliate.tiktok_user_id}</p>
              ) : (
                <p className="text-xs text-gray-600">ID dummy</p>
              )}
            </div>
          </button>
        </div>
      </div>

      {/* Step 3: Kirim Pesan */}
      <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5 space-y-4">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold text-white">3</div>
          <p className="text-sm font-semibold text-white">Kirim Pesan Simulasi</p>
          {selectedAffiliate && (
            <span className="text-xs text-gray-500">dari {selectedAffiliate.name}</span>
          )}
        </div>

        {/* Quick messages */}
        <div>
          <p className="text-xs text-gray-500 mb-2">Pesan cepat:</p>
          <div className="space-y-1.5">
            {sampleMessages.map((msg, i) => (
              <button key={i} onClick={() => handleQuickSend(msg)} disabled={sending || !selectedAffiliate}
                className="w-full flex items-center gap-3 rounded-lg border border-[#2f2f2f] px-3 py-2 text-left hover:border-violet-500/40 hover:bg-violet-950/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                <MessageCircle className="h-3.5 w-3.5 text-gray-500 shrink-0" />
                <span className="text-xs text-gray-300 truncate">{msg}</span>
                <Send className="h-3 w-3 text-gray-600 shrink-0 ml-auto" />
              </button>
            ))}
          </div>
        </div>

        {/* Custom message */}
        <div className="border-t border-[#1f1f1f] pt-4">
          <p className="text-xs text-gray-500 mb-2">Atau tulis pesan kustom:</p>
          <div className="flex gap-2">
            <textarea
              value={customMessage}
              onChange={e => setCustomMessage(e.target.value)}
              placeholder="Tulis pesan dari affiliator..."
              rows={2}
              disabled={!selectedAffiliate}
              className="flex-1 rounded-lg border border-[#2f2f2f] bg-[#0a0a0a] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none resize-none disabled:opacity-40"
            />
            <button onClick={handleCustomSend} disabled={!selectedAffiliate || !customMessage.trim() || sending}
              className="rounded-lg bg-violet-600 px-3 py-2 text-sm text-white hover:bg-violet-700 disabled:opacity-40 transition-colors shrink-0">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Bulk simulate */}
      <div className="rounded-xl border border-yellow-800/30 bg-yellow-950/10 p-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-yellow-400 flex items-center gap-2">
            <Users className="h-4 w-4" /> Simulasi Massal
          </p>
          <p className="text-xs text-gray-500 mt-0.5">Kirim 3 pesan sekaligus dari affiliator berbeda untuk test badge notifikasi</p>
        </div>
        <button onClick={handleBulkSimulate} disabled={sending}
          className="rounded-lg border border-yellow-600/40 px-4 py-2 text-sm text-yellow-400 hover:bg-yellow-900/20 disabled:opacity-40 transition-colors shrink-0">
          {sending ? 'Mengirim...' : 'Kirim 3 Pesan'}
        </button>
      </div>

      <p className="text-xs text-gray-600">
        Setelah mengirim, lonceng notifikasi di header akan menampilkan badge merah. Klik untuk melihat pesan masuk.
      </p>
    </div>
  )
}
