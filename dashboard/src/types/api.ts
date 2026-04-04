// TypeScript interfaces untuk API responses

export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: string
  role: string
}

export interface AffiliateCardResponse {
  id: string
  name: string
  photo_url: string | null
  follower_count: number
  engagement_rate: number
  content_categories: string[]
  location: string
  has_whatsapp: boolean
  gmv_total?: number
  rank?: number
}

export interface PaginatedAffiliateResponse {
  items: AffiliateCardResponse[]
  total: number
  page: number
  page_size: number
}

export interface AffiliateDetailResponse {
  id: string
  name: string
  photo_url: string | null
  follower_count: number
  engagement_rate: number
  content_categories: string[]
  location: string
  bio: string | null
  phone_number: string | null
  contact_channel: string
  whatsapp_collection_status: string | null
  tiktok_profile_url: string | null
}

export type CampaignStatus = 'ACTIVE' | 'DRAFT' | 'PAUSED' | 'STOPPED' | 'COMPLETED'

export interface CampaignResponse {
  id: string
  name: string
  description: string
  status: CampaignStatus
  start_date: string
  end_date: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface CampaignReportResponse {
  campaign_id: string
  campaign_name?: string
  total_influencers: number
  acceptance_rate: number
  total_views: number
  total_gmv: number
  cost_per_conversion: number
  generated_at: string
}

export interface GMVDataPoint {
  date: string
  gmv: number
}

export interface InfluencerFilters {
  min_followers?: number
  max_followers?: number
  min_engagement_rate?: number
  categories?: string[]
  locations?: string[]
  // Filter baru
  name?: string
  delivery_categories?: string[]
  sales_methods?: string[]
  has_whatsapp?: boolean
  invitation_status?: string
  sort_by?: string
  page: number
  page_size: number
}

export interface ExportReportRequest {
  format: 'csv' | 'excel' | 'pdf'
  campaign_ids?: string[]
  start_date?: string
  end_date?: string
}

export const queryKeys = {
  reports: ['reports', 'campaigns'] as const,
  affiliates: (filters: InfluencerFilters) => ['affiliates', filters] as const,
  affiliateDetail: (id: string) => ['affiliates', id] as const,
  campaigns: ['campaigns'] as const,
  campaignReport: (id: string) => ['campaigns', id, 'report'] as const,
}

// Analytics Platform Types

export interface OverviewResponse {
  total_gmv: number
  total_views: number
  total_creators: number
  global_conversion_rate: number
  total_buyers: number
  top_creator_name: string
  top_creator_revenue: number
  top_product_name: string
  top_product_gmv: number
}

export interface CreatorIntelligenceItem {
  id: string
  name: string
  location: string
  follower_count: number
  engagement_rate: number
  avg_views: number
  estimated_revenue: number
  creator_score: number
  creator_role: string
  video_count: number
  total_views: number
  total_gmv: number
  content_categories: string[]
  has_whatsapp: boolean
}

export interface ContentItem {
  id: string
  tiktok_video_id: string
  creator_name: string
  product_name: string | null
  title: string
  views: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number
  gmv_generated: number
  conversion_rate: number
  velocity: number
  posted_at: string
}

export interface ProductItem {
  id: string
  name: string
  category: string
  price: number
  shop_name: string
  total_creators: number
  total_views: number
  total_gmv: number
  conversion_rate: number
  total_buyers: number
  revenue: number
}

export interface RevenueInsightItem {
  creator_id: string
  creator_name: string
  product_id: string | null
  product_name: string | null
  video_count: number
  revenue: number
  gmv: number
  buyers: number
  conversion_rate: number
}
