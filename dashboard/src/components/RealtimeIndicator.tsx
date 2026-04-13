'use client'
import { useRealtimeStats } from '@/hooks/useRealtimeStats'
import { Activity, MessageCircle, Users, Zap } from 'lucide-react'

function timeAgo(date: Date): string {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diff < 60) return `${diff}d lalu`
  return `${Math.floor(diff / 60)}m lalu`
}

export function RealtimeIndicator() {
  const { stats, connected, lastUpdated } = useRealtimeStats()

  return (
    <div className="flex items-center gap-3">
      {/* Live stats pills */}
      {stats && (
        <div className="hidden md:flex items-center gap-2">
          {stats.unread_count > 0 && (
            <div className="flex items-center gap-1.5 rounded-full bg-violet-900/20 border border-violet-900/30 px-2.5 py-1">
              <MessageCircle className="h-3 w-3 text-violet-400" />
              <span className="text-xs text-violet-400">{stats.unread_count} pesan baru</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 rounded-full bg-[#1a1a1a] border border-[#2f2f2f] px-2.5 py-1">
            <Users className="h-3 w-3 text-gray-400" />
            <span className="text-xs text-gray-400">{stats.active_affiliates} aktif</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-full bg-[#1a1a1a] border border-[#2f2f2f] px-2.5 py-1">
            <Zap className="h-3 w-3 text-yellow-400" />
            <span className="text-xs text-gray-400">{stats.messages_today} pesan hari ini</span>
          </div>
        </div>
      )}

      {/* Connection status */}
      <div className="flex items-center gap-1.5 rounded-full bg-[#1a1a1a] border border-[#2f2f2f] px-2.5 py-1">
        <Activity className={`h-3 w-3 ${connected ? 'text-green-400' : 'text-gray-600'}`} />
        <span className={`text-xs ${connected ? 'text-green-400' : 'text-gray-600'}`}>
          {connected ? 'Live' : lastUpdated ? timeAgo(lastUpdated) : 'Offline'}
        </span>
        {connected && (
          <div className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
        )}
      </div>
    </div>
  )
}
