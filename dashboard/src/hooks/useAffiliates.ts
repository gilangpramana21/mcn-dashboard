import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  PaginatedAffiliateResponse,
  AffiliateDetailResponse,
  InfluencerFilters,
} from '@/types/api'
import { queryKeys } from '@/types/api'

/**
 * Membangun query params dari InfluencerFilters secara deterministik.
 * Input yang sama selalu menghasilkan output yang sama.
 */
export function buildAffiliateQueryParams(filters: InfluencerFilters): Record<string, string> {
  const params: Record<string, string> = {
    page: String(filters.page),
    page_size: String(filters.page_size),
  }
  if (filters.min_followers != null) params.min_followers = String(filters.min_followers)
  if (filters.max_followers != null) params.max_followers = String(filters.max_followers)
  if (filters.min_engagement_rate != null)
    params.min_engagement_rate = String(filters.min_engagement_rate)
  if (filters.categories?.length) params.categories = filters.categories.join(',')
  if (filters.locations?.length) params.locations = filters.locations.join(',')
  // Params baru
  if (filters.name) params.name = filters.name
  if (filters.delivery_categories?.length) params.delivery_categories = filters.delivery_categories.join(',')
  if (filters.sales_methods?.length) params.sales_methods = filters.sales_methods.join(',')
  if (filters.has_whatsapp != null) params.has_whatsapp = String(filters.has_whatsapp)
  if (filters.invitation_status) params.invitation_status = filters.invitation_status
  if (filters.sort_by) params.sort_by = filters.sort_by
  return params
}

export function useAffiliates(filters: InfluencerFilters) {
  return useQuery({
    queryKey: queryKeys.affiliates(filters),
    queryFn: async () => {
      const params = buildAffiliateQueryParams(filters)
      const searchParams = new URLSearchParams(params).toString()
      const res = await apiClient.get<PaginatedAffiliateResponse>(
        `/affiliates/search?${searchParams}`
      )
      return (res as any).data ?? res
    },
  })
}

export function useAffiliateDetail(id: string) {
  return useQuery({
    queryKey: queryKeys.affiliateDetail(id),
    queryFn: () => apiClient.get<{ data: AffiliateDetailResponse }>(`/affiliates/${id}`).then(r => r.data),
    enabled: !!id,
  })
}
