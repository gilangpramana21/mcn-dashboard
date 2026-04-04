'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useAffiliateDetail } from '@/hooks/useAffiliates'
import { GMVChart } from '@/components/GMVChart'
import type { ChartMode } from '@/components/GMVChart'
import type { GMVDataPoint } from '@/types/api'
import { formatFollowerCount, formatEngagementRate, formatCurrency } from '@/lib/formatters'

// Mock GMV trend data (API tidak mengembalikan histori GMV langsung)
function generateMockGMVData(mode: ChartMode): GMVDataPoint[] {
  const now = new Date()
  const points: GMVDataPoint[] = []

  if (mode === 'monthly') {
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      points.push({
        date: d.toISOString().split('T')[0],
        gmv: Math.floor(Math.random() * 50_000_000) + 5_000_000,
      })
    }
  } else if (mode === 'weekly') {
    for (let i = 7; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i * 7)
      points.push({
        date: d.toISOString().split('T')[0],
        gmv: Math.floor(Math.random() * 15_000_000) + 1_000_000,
      })
    }
  } else {
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      points.push({
        date: d.toISOString().split('T')[0],
        gmv: Math.floor(Math.random() * 5_000_000) + 500_000,
      })
    }
  }

  return points
}

// Mock campaign history
const MOCK_CAMPAIGNS = [
  { id: '1', name: 'Kampanye Ramadan 2024', gmv: 45_000_000, status: 'COMPLETED' },
  { id: '2', name: 'Flash Sale Harbolnas', gmv: 32_000_000, status: 'COMPLETED' },
  { id: '3', name: 'Koleksi Lebaran', gmv: 28_500_000, status: 'COMPLETED' },
  { id: '4', name: 'Back to School', gmv: 19_200_000, status: 'ACTIVE' },
]

const COMMISSION_RATE = 0.05

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-[#1f1f1f] ${className ?? ''}`} />
}

function DetailSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <SkeletonBlock className="h-8 w-32" />
      <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-6">
        <div className="flex items-start gap-6">
          <SkeletonBlock className="h-24 w-24 rounded-full" />
          <div className="flex-1 space-y-3">
            <SkeletonBlock className="h-7 w-48" />
            <SkeletonBlock className="h-4 w-full max-w-md" />
            <SkeletonBlock className="h-4 w-64" />
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <SkeletonBlock key={i} className="h-24 rounded-lg" />
        ))}
      </div>
      <SkeletonBlock className="h-72 rounded-lg" />
      <SkeletonBlock className="h-48 rounded-lg" />
    </div>
  )
}

export default function InfluencerDetailPage({
  params,
}: {
  params: { id: string }
}) {
  const router = useRouter()
  const { id } = params
  const [chartMode, setChartMode] = useState<ChartMode>('monthly')

  const { data, isLoading, error } = useAffiliateDetail(id)

  // Handle 404
  const is404 =
    (error as any)?.response?.status === 404 ||
    (error as any)?.status === 404

  if (isLoading) {
    return <DetailSkeleton />
  }

  if (is404 || (!isLoading && !data?.data && error)) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6">
        <p className="text-2xl font-bold text-white">Influencer tidak ditemukan</p>
        <p className="text-sm text-gray-400">
          Influencer dengan ID <span className="font-mono text-gray-300">{id}</span> tidak ada.
        </p>
        <button
          onClick={() => router.back()}
          className="rounded bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
        >
          ← Kembali
        </button>
      </div>
    )
  }

  const influencer = data?.data

  if (!influencer) return null

  const gmvData = generateMockGMVData(chartMode)
  const totalGmv = MOCK_CAMPAIGNS.reduce((sum, c) => sum + c.gmv, 0)
  const commissionEstimate = totalGmv * COMMISSION_RATE

  return (
    <div className="space-y-6 p-6">
      {/* Back button */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors"
      >
        ← Kembali ke Daftar
      </button>

      {/* Profile Card */}
      <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
          {/* Photo */}
          <div className="flex-shrink-0">
            {influencer.photo_url ? (
              <Image
                src={influencer.photo_url}
                alt={influencer.name}
                width={96}
                height={96}
                className="rounded-full object-cover"
                unoptimized
              />
            ) : (
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-[#1f1f1f] text-3xl font-bold text-gray-400">
                {influencer.name.charAt(0).toUpperCase()}
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 space-y-3">
            <div>
              <h1 className="text-2xl font-bold text-white">{influencer.name}</h1>
              {influencer.location && (
                <p className="mt-1 text-sm text-gray-400">📍 {influencer.location}</p>
              )}
            </div>

            {influencer.bio && (
              <p className="text-sm leading-relaxed text-gray-300">{influencer.bio}</p>
            )}

            {/* Categories */}
            {influencer.content_categories.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {influencer.content_categories.map((cat) => (
                  <span
                    key={cat}
                    className="rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-0.5 text-xs font-medium text-violet-300"
                  >
                    {cat}
                  </span>
                ))}
              </div>
            )}

            {/* TikTok link */}
            {influencer.tiktok_profile_url && (
              <a
                href={influencer.tiktok_profile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-violet-400 hover:text-violet-300 transition-colors"
              >
                🎵 Profil TikTok
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-4">
          <p className="text-xs text-gray-400">Followers</p>
          <p className="mt-1 text-2xl font-bold text-white">
            {formatFollowerCount(influencer.follower_count)}
          </p>
        </div>
        <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-4">
          <p className="text-xs text-gray-400">Engagement Rate</p>
          <p className="mt-1 text-2xl font-bold text-white">
            {formatEngagementRate(influencer.engagement_rate)}
          </p>
        </div>
        <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-4">
          <p className="text-xs text-gray-400">Total GMV</p>
          <p className="mt-1 text-2xl font-bold text-white">
            {formatCurrency(totalGmv)}
          </p>
        </div>
        <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-4">
          <p className="text-xs text-gray-400">Estimasi Komisi (5%)</p>
          <p className="mt-1 text-2xl font-bold text-violet-400">
            {formatCurrency(commissionEstimate)}
          </p>
        </div>
      </div>

      {/* GMV Chart */}
      <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-6">
        <h2 className="mb-4 text-sm font-semibold text-gray-300">Tren GMV</h2>
        <GMVChart
          data={gmvData}
          mode={chartMode}
          onModeChange={setChartMode}
        />
      </div>

      {/* Campaign History Table */}
      <div className="rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] p-6">
        <h2 className="mb-4 text-sm font-semibold text-gray-300">Riwayat Kampanye</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1f1f1f] text-left text-xs text-gray-400">
              <th className="pb-3 font-medium">Kampanye</th>
              <th className="pb-3 font-medium">Status</th>
              <th className="pb-3 text-right font-medium">GMV</th>
              <th className="pb-3 text-right font-medium">Komisi (5%)</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_CAMPAIGNS.map((campaign) => (
              <tr
                key={campaign.id}
                className="border-b border-[#1f1f1f] last:border-0"
              >
                <td className="py-3 text-white">{campaign.name}</td>
                <td className="py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      campaign.status === 'ACTIVE'
                        ? 'bg-green-500/10 text-green-400'
                        : 'bg-gray-500/10 text-gray-400'
                    }`}
                  >
                    {campaign.status}
                  </span>
                </td>
                <td className="py-3 text-right text-white">
                  {formatCurrency(campaign.gmv)}
                </td>
                <td className="py-3 text-right text-violet-400">
                  {formatCurrency(campaign.gmv * COMMISSION_RATE)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-[#1f1f1f]">
              <td colSpan={2} className="pt-3 text-xs font-semibold text-gray-400">
                Total
              </td>
              <td className="pt-3 text-right text-sm font-bold text-white">
                {formatCurrency(totalGmv)}
              </td>
              <td className="pt-3 text-right text-sm font-bold text-violet-400">
                {formatCurrency(commissionEstimate)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
