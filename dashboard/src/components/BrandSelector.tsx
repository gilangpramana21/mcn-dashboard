'use client'
import { useState, useRef, useEffect } from 'react'
import { useBrand } from '@/contexts/BrandContext'
import { ChevronDown, Building2, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'

export function BrandSelector() {
  const { brands, activeBrandId, activeBrand, setActiveBrandId } = useBrand()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  if (brands.length === 0) return null

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 rounded-lg border border-[#2f2f2f] bg-[#111111] px-3 py-1.5 text-sm text-white hover:border-violet-500/50 transition-colors"
      >
        {activeBrand ? (
          <>
            <div className="h-5 w-5 rounded bg-violet-600/20 flex items-center justify-center shrink-0">
              <span className="text-xs font-bold text-violet-400">{activeBrand.name.charAt(0)}</span>
            </div>
            <span className="max-w-[120px] truncate">{activeBrand.name}</span>
          </>
        ) : (
          <>
            <Globe className="h-4 w-4 text-gray-400" />
            <span className="text-gray-400">Semua Brand</span>
          </>
        )}
        <ChevronDown className={cn('h-3.5 w-3.5 text-gray-500 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-52 rounded-xl border border-[#1f1f1f] bg-[#111111] shadow-2xl z-50 overflow-hidden">
          {/* Semua Brand */}
          <button
            onClick={() => { setActiveBrandId(null); setOpen(false) }}
            className={cn(
              'flex items-center gap-2.5 w-full px-3 py-2.5 text-sm text-left hover:bg-[#1a1a1a] transition-colors',
              !activeBrandId ? 'text-violet-400 bg-violet-950/20' : 'text-gray-400'
            )}
          >
            <Globe className="h-4 w-4 shrink-0" />
            <span>Semua Brand</span>
            {!activeBrandId && <div className="ml-auto h-1.5 w-1.5 rounded-full bg-violet-500" />}
          </button>

          <div className="border-t border-[#1f1f1f]" />

          {/* Brand list */}
          <div className="max-h-56 overflow-y-auto">
            {brands.map(brand => (
              <button
                key={brand.id}
                onClick={() => { setActiveBrandId(brand.id); setOpen(false) }}
                className={cn(
                  'flex items-center gap-2.5 w-full px-3 py-2.5 text-sm text-left hover:bg-[#1a1a1a] transition-colors',
                  activeBrandId === brand.id ? 'text-violet-400 bg-violet-950/20' : 'text-gray-300'
                )}
              >
                <div className="h-6 w-6 rounded bg-violet-600/20 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-violet-400">{brand.name.charAt(0)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate">{brand.name}</p>
                  <p className="text-xs text-gray-600">{brand.sku_count} SKU</p>
                </div>
                {activeBrandId === brand.id && <div className="h-1.5 w-1.5 rounded-full bg-violet-500 shrink-0" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
