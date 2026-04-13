'use client'
import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { Bell, Phone, Store, Check, CheckCheck, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface InboxMessage {
  id: string
  affiliate_name: string
  channel: 'whatsapp' | 'tiktok_seller'
  message_content: string
  from_number: string | null
  is_read: boolean
  received_at: string
}

const CHANNEL_CONFIG = {
  whatsapp: { icon: Phone, color: 'text-green-400', bg: 'bg-green-900/20', label: 'WhatsApp' },
  tiktok_seller: { icon: Store, color: 'text-pink-400', bg: 'bg-pink-900/20', label: 'TikTok Seller' },
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Baru saja'
  if (mins < 60) return `${mins} menit lalu`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} jam lalu`
  return `${Math.floor(hours / 24)} hari lalu`
}

// Singleton AudioContext — dibuat sekali, di-resume saat user interact
let _audioCtx: AudioContext | null = null

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (!_audioCtx) {
    try {
      _audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    } catch {
      return null
    }
  }
  return _audioCtx
}

// Unlock AudioContext saat user pertama kali klik — wajib untuk autoplay policy
if (typeof window !== 'undefined') {
  const unlock = () => {
    const ctx = getAudioContext()
    if (ctx && ctx.state === 'suspended') ctx.resume()
    window.removeEventListener('click', unlock)
    window.removeEventListener('keydown', unlock)
    window.removeEventListener('touchstart', unlock)
  }
  window.addEventListener('click', unlock)
  window.addEventListener('keydown', unlock)
  window.addEventListener('touchstart', unlock)
}

async function playNotificationSound() {
  const ctx = getAudioContext()
  if (!ctx) return
  try {
    if (ctx.state === 'suspended') await ctx.resume()
    const notes = [880, 1100]
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.type = 'sine'
      osc.frequency.value = freq
      const start = ctx.currentTime + i * 0.13
      gain.gain.setValueAtTime(0, start)
      gain.gain.linearRampToValueAtTime(0.35, start + 0.01)
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.18)
      osc.start(start)
      osc.stop(start + 0.2)
    })
  } catch {
    // skip jika gagal
  }
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const qc = useQueryClient()
  const prevCount = useRef(0)
  const router = useRouter()

  const { data: countData } = useQuery({
    queryKey: ['inbox-count'],
    queryFn: () => apiClient.get('/inbox/unread-count').then(r => (r as any).data ?? r),
    refetchInterval: 30000, // poll setiap 30 detik (SSE sudah handle real-time)
    retry: false,
  })

  const { data: messages = [] } = useQuery({
    queryKey: ['inbox'],
    queryFn: () => apiClient.get('/inbox').then(r => (r as any).data ?? r),
    enabled: open,
    retry: false,
  })

  const markRead = useMutation({
    mutationFn: (id: string) => apiClient.patch(`/inbox/${id}/read`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inbox-count'] })
      qc.invalidateQueries({ queryKey: ['inbox'] })
    },
  })

  const markAllRead = useMutation({
    mutationFn: () => apiClient.patch('/inbox/read-all'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inbox-count'] })
      qc.invalidateQueries({ queryKey: ['inbox'] })
      toast.success('Semua pesan ditandai sudah dibaca')
    },
  })

  const unreadCount = countData?.count ?? 0

  // Toast + suara saat ada pesan baru
  useEffect(() => {
    if (unreadCount > prevCount.current && prevCount.current > 0) {
      playNotificationSound()
      toast.info(`${unreadCount - prevCount.current} pesan baru masuk`, {
        description: 'Klik lonceng untuk melihat',
      })
    }
    prevCount.current = unreadCount
  }, [unreadCount])

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="relative flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-[#1a1a1a] hover:text-white transition-colors"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-[#1f1f1f] bg-[#111111] shadow-2xl z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#1f1f1f]">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-violet-400" />
              <span className="text-sm font-semibold text-white">Pesan Masuk</span>
              {unreadCount > 0 && (
                <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-xs text-red-400">
                  {unreadCount} baru
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={() => markAllRead.mutate()}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-violet-400 transition-colors px-2 py-1"
                  title="Tandai semua dibaca"
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                </button>
              )}
              <button onClick={() => setOpen(false)} className="text-gray-600 hover:text-white transition-colors p-1">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Message list */}
          <div className="max-h-80 overflow-y-auto divide-y divide-[#1f1f1f]">
            {(messages as InboxMessage[]).length === 0 ? (
              <div className="p-8 text-center">
                <Bell className="h-8 w-8 text-gray-700 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Belum ada pesan masuk</p>
              </div>
            ) : (
              (messages as InboxMessage[]).map(msg => {
                const ch = CHANNEL_CONFIG[msg.channel] ?? CHANNEL_CONFIG.whatsapp
                const Icon = ch.icon
                return (
                  <div
                    key={msg.id}
                    className={cn(
                      'flex items-start gap-3 px-4 py-3 hover:bg-[#1a1a1a] transition-colors cursor-pointer',
                      !msg.is_read && 'bg-violet-950/20'
                    )}
                    onClick={() => {
                      if (!msg.is_read) markRead.mutate(msg.id)
                      setOpen(false)
                      const url = `/messages?affiliate=${encodeURIComponent(msg.affiliate_name)}`
                      // Pakai replace agar selalu trigger re-render meski sudah di halaman messages
                      router.replace(url)
                    }}
                  >
                    <div className={cn('h-8 w-8 rounded-full flex items-center justify-center shrink-0', ch.bg)}>
                      <Icon className={cn('h-4 w-4', ch.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-white truncate">{msg.affiliate_name}</p>
                        {!msg.is_read && (
                          <div className="h-2 w-2 rounded-full bg-violet-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{msg.message_content}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={cn('text-xs', ch.color)}>{ch.label}</span>
                        {msg.from_number && (
                          <span className="text-xs text-gray-600">{msg.from_number}</span>
                        )}
                        <span className="text-xs text-gray-600 ml-auto">{timeAgo(msg.received_at)}</span>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Footer — link ke halaman messages */}
          <div className="border-t border-[#1f1f1f] px-4 py-2.5">
            <a href="/messages" className="text-xs text-violet-400 hover:text-violet-300 transition-colors">
              Lihat semua pesan →
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
