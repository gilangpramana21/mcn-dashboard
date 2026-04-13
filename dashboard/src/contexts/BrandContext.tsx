'use client'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

interface Brand {
  id: string
  name: string
  wa_number: string | null
  sku_count: number
}

interface BrandContextValue {
  brands: Brand[]
  activeBrandId: string | null
  activeBrand: Brand | null
  setActiveBrandId: (id: string | null) => void
}

const BrandContext = createContext<BrandContextValue>({
  brands: [],
  activeBrandId: null,
  activeBrand: null,
  setActiveBrandId: () => {},
})

export function BrandProvider({ children }: { children: ReactNode }) {
  const [activeBrandId, setActiveBrandIdState] = useState<string | null>(null)

  const { data: brands = [] } = useQuery<Brand[]>({
    queryKey: ['brands'],
    queryFn: () => apiClient.get('/brands').then(r => (r as any).data ?? r),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  // Restore dari localStorage
  useEffect(() => {
    const saved = localStorage.getItem('activeBrandId')
    if (saved) setActiveBrandIdState(saved)
  }, [])

  function setActiveBrandId(id: string | null) {
    setActiveBrandIdState(id)
    if (id) localStorage.setItem('activeBrandId', id)
    else localStorage.removeItem('activeBrandId')
  }

  const activeBrand = brands.find(b => b.id === activeBrandId) ?? null

  return (
    <BrandContext.Provider value={{ brands, activeBrandId, activeBrand, setActiveBrandId }}>
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  return useContext(BrandContext)
}
