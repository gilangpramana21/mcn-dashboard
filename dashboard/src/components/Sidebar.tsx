'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Users, Search, FileText, Ban, 
  Brain, ShieldCheck, DollarSign, Play, ShoppingBag, Zap, MessageSquare, Upload, Bot, UserCog,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { features } from '@/lib/features'

const NAV_SECTIONS = [
  {
    label: 'Analytics',
    items: [
      { href: '/', label: 'Dashboard', icon: LayoutDashboard, role: null, waOnly: false },
      { href: '/creator-intelligence', label: 'Analitik Affiliator', icon: Users, role: null, waOnly: false },
      { href: '/content-analytics', label: 'Content Analytics', icon: Play, role: null, waOnly: false },
      { href: '/product-analytics', label: 'Product Analytics', icon: ShoppingBag, role: null, waOnly: false },
      { href: '/revenue-insights', label: 'Revenue Insights', icon: DollarSign, role: null, waOnly: false },
    ],
  },
  {
    label: 'Outreach',
    items: [
      { href: '/affiliates', label: 'Cari Affiliasi', icon: Search, role: null, waOnly: false },
      { href: '/import', label: 'Import Affiliator', icon: Upload, role: 'manager', waOnly: false },
      { href: '/messages', label: 'History Pesan', icon: MessageSquare, role: null, waOnly: true },
      { href: '/templates', label: 'Template Pesan', icon: FileText, role: 'manager', waOnly: true },
      { href: '/blacklist', label: 'Daftar Hitam', icon: Ban, role: 'manager', waOnly: false },
    ],
  },
  {
    label: 'AI',
    items: [
      { href: '/agent', label: 'TikTok Shop Agent', icon: Bot, role: 'manager', waOnly: false },
      { href: '/learning', label: 'AI Learning', icon: Brain, role: null, waOnly: false },
    ],
  },
  {
    label: 'Pengaturan',
    items: [
      { href: '/users', label: 'Manajemen Akun', icon: UserCog, role: 'admin', waOnly: false },
    ],
  },
]

const ROLE_LABELS: Record<string, string> = {
  'Administrator': 'Administrator',
  'Manajer_Kampanye': 'Manajer Kampanye',
  'Peninjau': 'Peninjau',
}

const ROLE_COLORS: Record<string, string> = {
  'Administrator': 'bg-red-900/40 text-red-400',
  'Manajer_Kampanye': 'bg-violet-900/40 text-violet-400',
  'Peninjau': 'bg-gray-800 text-gray-400',
}

export function Sidebar() {
  const pathname = usePathname()
  const { role, isManager, isAdmin } = useAuth()

  function isVisible(itemRole: string | null, waOnly: boolean) {
    if (waOnly && !features.showWhatsApp) return false
    if (itemRole === null) return true
    if (itemRole === 'manager') return isManager
    if (itemRole === 'admin') return isAdmin
    return true
  }

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-[#1f1f1f] bg-[#0d0d0d]">
      <div className="flex h-14 items-center px-4 border-b border-[#1f1f1f]">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-md bg-violet-600 flex items-center justify-center">
            <Zap className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold text-white">MCN Dashboard</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-4">
        {NAV_SECTIONS.map(section => {
          const visibleItems = section.items.filter(item => isVisible(item.role, item.waOnly))
          if (visibleItems.length === 0) return null
          return (
            <div key={section.label}>
              <p className="text-xs font-medium text-gray-600 px-3 mb-1.5 uppercase tracking-wider">{section.label}</p>
              <div className="space-y-0.5">
                {visibleItems.map(({ href, label, icon: Icon }) => {
                  const isActive = pathname === href || (href !== '/' && pathname.startsWith(href))
                  return (
                    <Link key={href} href={href}
                      className={cn(
                        'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors',
                        isActive
                          ? 'bg-violet-600/20 text-violet-400'
                          : 'text-gray-400 hover:bg-[#1a1a1a] hover:text-white'
                      )}>
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{label}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          )
        })}
      </nav>

      {role && (
        <div className="p-3 border-t border-[#1f1f1f]">
          <div className={cn('flex items-center gap-2 rounded-lg px-3 py-2 text-xs', ROLE_COLORS[role] ?? 'bg-gray-800 text-gray-400')}>
            <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
            <span>{ROLE_LABELS[role] ?? role}</span>
          </div>
        </div>
      )}
    </aside>
  )
}
