import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

interface UseAnalyticsOptions {
  enabled?: boolean
  refetchInterval?: number
}

export function useAnalytics<T>(
  endpoint: string,
  params?: Record<string, any>,
  options?: UseAnalyticsOptions
) {
  const queryKey = ['analytics', endpoint, params]
  
  const { data, isLoading, error, refetch } = useQuery<T>({
    queryKey,
    queryFn: async () => {
      const response = await apiClient.get(`/analytics/${endpoint}`, { params })
      // Backend returns { data: {...}, meta: {} }, extract the data field
      return response.data.data || response.data
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  return {
    data,
    loading: isLoading,
    error,
    refetch,
  }
}
