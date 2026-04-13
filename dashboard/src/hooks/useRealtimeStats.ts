'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export interface RealtimeStats {
  unread_count: number
  total_conversations: number
  active_affiliates: number
  messages_today: number
  recent_messages: Array<{
    affiliate_name: string
    channel: string
    message_content: string
    received_at: string
  }>
}

export function useRealtimeStats() {
  const [stats, setStats] = useState<RealtimeStats | null>(null)
  const [connected, setConnected] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const qc = useQueryClient()
  const prevUnread = useRef(0)

  const connect = useCallback(() => {
    // Ambil token dari localStorage/cookie
    const token = typeof window !== 'undefined'
      ? localStorage.getItem('auth_token')
      : null

    if (!token) return

    const url = `/api/v1/realtime/stats`

    // Fetch dengan Authorization header (EventSource tidak support header langsung)
    // Gunakan fetch + ReadableStream sebagai workaround
    const controller = new AbortController()

    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    }).then(async (res) => {
      if (!res.ok || !res.body) {
        setConnected(false)
        return
      }
      setConnected(true)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: RealtimeStats = JSON.parse(line.slice(6))
              setStats(data)
              setLastUpdated(new Date())

              // Invalidate inbox-count query jika unread berubah
              if (data.unread_count !== prevUnread.current) {
                qc.invalidateQueries({ queryKey: ['inbox-count'] })
                prevUnread.current = data.unread_count
              }
            } catch {
              // skip malformed JSON
            }
          }
        }
      }
      setConnected(false)
    }).catch(() => {
      setConnected(false)
    })

    return controller
  }, [qc])

  useEffect(() => {
    let controller: AbortController | undefined

    // Delay sedikit agar token sudah tersedia
    const timer = setTimeout(() => {
      controller = connect()
    }, 1000)

    return () => {
      clearTimeout(timer)
      controller?.abort()
      setConnected(false)
    }
  }, [connect])

  return { stats, connected, lastUpdated }
}
