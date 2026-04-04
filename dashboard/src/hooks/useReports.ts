import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { CampaignReportResponse } from '@/types/api'
import { queryKeys } from '@/types/api'

export function useReports() {
  return useQuery({
    queryKey: queryKeys.reports,
    queryFn: async () => {
      const res = await apiClient.get<CampaignReportResponse[] | CampaignReportResponse>(
        '/api/v1/reports/campaigns'
      )
      const data = (res as any).data ?? res
      return Array.isArray(data) ? data : [data]
    },
  })
}

/**
 * Hitung ROI per kampanye.
 * ROI = (total_gmv - cost * total_influencers) / (cost * total_influencers) * 100
 * Mengembalikan nilai finite; 0 jika denominator = 0.
 */
export function calculateROI(
  totalGmv: number,
  costPerConversion: number,
  totalInfluencers: number
): number {
  const denominator = costPerConversion * totalInfluencers
  if (denominator === 0) return 0
  const roi = ((totalGmv - denominator) / denominator) * 100
  return isFinite(roi) ? roi : 0
}
