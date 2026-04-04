import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { CampaignResponse, CampaignReportResponse } from '@/types/api'
import { queryKeys } from '@/types/api'

export function useCampaigns() {
  return useQuery({
    queryKey: queryKeys.campaigns,
    queryFn: async () => {
      const res = await apiClient.get<CampaignResponse[]>('/api/v1/campaigns')
      const data = (res as any).data ?? res
      return Array.isArray(data) ? data : (data as any).items ?? []
    },
  })
}

export function useCampaignReport(id: string) {
  return useQuery({
    queryKey: queryKeys.campaignReport(id),
    queryFn: () =>
      apiClient.get<CampaignReportResponse>(`/api/v1/campaigns/${id}/report`),
    enabled: !!id,
  })
}
