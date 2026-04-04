'use client'
import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Brain, TrendingUp, Zap, BarChart2, RefreshCw, ChevronUp, ChevronDown, Minus } from 'lucide-react'

interface ModelVersion {
  id: string
  model_type: string
  version: number
  accuracy_before: number | null
  accuracy_after: number
  trained_at: string
  training_data_size: number
}

interface Recommendation {
  influencer_id: string
  predicted_conversion_rate: number
  predicted_gmv: number
  confidence_score: number
  based_on_campaigns: string[]
}

function AccuracyBadge({ before, after }: { before: number | null; after: number }) {
  const pct = (after * 100).toFixed(1)
  const color = after >= 0.85 ? 'text-green-400' : after >= 0.70 ? 'text-yellow-400' : 'text-red-400'
  const bg = after >= 0.85 ? 'bg-green-900/20' : after >= 0.70 ? 'bg-yellow-900/20' : 'bg-red-900/20'

  return (
    <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 ${bg}`}>
      {before !== null ? (
        <>
          <span className="text-gray-500 text-xs">{(before * 100).toFixed(1)}%</span>
          {after > before ? <ChevronUp className="h-3 w-3 text-green-400" /> :
           after < before ? <ChevronDown className="h-3 w-3 text-red-400" /> :
           <Minus className="h-3 w-3 text-gray-500" />}
        </>
      ) : null}
      <span className={`text-xs font-bold ${color}`}>{pct}%</span>
    </div>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-[#1a1a1a]">
        <div className={`h-1.5 rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  )
}

export default function LearningPage() {
  const [history, setHistory] = useState<ModelVersion[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'selection' | 'classifier'>('selection')

  async function load() {
    setIsLoading(true)
    try {
      const [histRes, recRes] = await Promise.allSettled([
        apiClient.get('/learning/model-history'),
        apiClient.get('/learning/recommendations?top_n=10'),
      ])
      if (histRes.status === 'fulfilled') setHistory(histRes.value.data ?? [])
      if (recRes.status === 'fulfilled') setRecommendations(recRes.value.data ?? [])
    } finally { setIsLoading(false) }
  }

  useEffect(() => { load() }, [])

  const selectionModels = history.filter(m => m.model_type === 'SELECTION')
  const classifierModels = history.filter(m => m.model_type === 'CLASSIFIER')
  const latestSelection = selectionModels[0]
  const latestClassifier = classifierModels[0]

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">AI Learning Engine</h1>
          <p className="text-sm text-gray-500 mt-0.5">Model self-improving berbasis data historis kampanye</p>
        </div>
        <button onClick={load} disabled={isLoading}
          className="flex items-center gap-2 rounded-lg border border-[#1f1f1f] px-3 py-2 text-sm text-gray-400 hover:text-white hover:border-violet-500/40 transition-colors disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Model Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-violet-600/20 flex items-center justify-center">
                <Brain className="h-4 w-4 text-violet-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Model Seleksi</p>
                <p className="text-xs text-gray-500">Rekomendasi influencer</p>
              </div>
            </div>
            {latestSelection && <AccuracyBadge before={latestSelection.accuracy_before} after={latestSelection.accuracy_after} />}
          </div>
          {latestSelection ? (
            <div className="space-y-1.5 text-xs text-gray-500">
              <div className="flex justify-between"><span>Versi terkini</span><span className="text-white">v{latestSelection.version}</span></div>
              <div className="flex justify-between"><span>Data training</span><span className="text-white">{latestSelection.training_data_size} sampel</span></div>
              <div className="flex justify-between"><span>Terlatih</span><span className="text-white">{new Date(latestSelection.trained_at).toLocaleDateString('id-ID')}</span></div>
              <div className="flex justify-between"><span>Total versi</span><span className="text-white">{selectionModels.length}</span></div>
            </div>
          ) : (
            <p className="text-xs text-gray-600">Belum ada model. Selesaikan kampanye untuk melatih.</p>
          )}
        </div>

        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-blue-600/20 flex items-center justify-center">
                <Zap className="h-4 w-4 text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Model Klasifikasi</p>
                <p className="text-xs text-gray-500">Klasifikasi feedback NLP</p>
              </div>
            </div>
            {latestClassifier && <AccuracyBadge before={latestClassifier.accuracy_before} after={latestClassifier.accuracy_after} />}
          </div>
          {latestClassifier ? (
            <div className="space-y-1.5 text-xs text-gray-500">
              <div className="flex justify-between"><span>Versi terkini</span><span className="text-white">v{latestClassifier.version}</span></div>
              <div className="flex justify-between"><span>Data training</span><span className="text-white">{latestClassifier.training_data_size} sampel</span></div>
              <div className="flex justify-between"><span>Terlatih</span><span className="text-white">{new Date(latestClassifier.trained_at).toLocaleDateString('id-ID')}</span></div>
              <div className="flex justify-between"><span>Total versi</span><span className="text-white">{classifierModels.length}</span></div>
            </div>
          ) : (
            <p className="text-xs text-gray-600">Belum ada model. Klasifikasi feedback untuk melatih.</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model History */}
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
          <div className="border-b border-[#1f1f1f] px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart2 className="h-4 w-4 text-violet-400" />
              <h2 className="text-sm font-semibold text-white">Riwayat Versi Model</h2>
            </div>
            <div className="flex rounded-lg border border-[#1f1f1f] overflow-hidden text-xs">
              <button onClick={() => setActiveTab('selection')}
                className={`px-3 py-1.5 transition-colors ${activeTab === 'selection' ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                Seleksi
              </button>
              <button onClick={() => setActiveTab('classifier')}
                className={`px-3 py-1.5 transition-colors ${activeTab === 'classifier' ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                Klasifikasi
              </button>
            </div>
          </div>
          <div className="divide-y divide-[#1f1f1f]">
            {isLoading && Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse bg-[#0d0d0d] m-3 rounded-lg" />
            ))}
            {!isLoading && (activeTab === 'selection' ? selectionModels : classifierModels).length === 0 && (
              <div className="p-8 text-center text-gray-600 text-sm">Belum ada riwayat model</div>
            )}
            {!isLoading && (activeTab === 'selection' ? selectionModels : classifierModels).map(m => (
              <div key={m.id} className="px-5 py-3 flex items-center justify-between hover:bg-[#0d0d0d] transition-colors">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-white text-sm font-medium">v{m.version}</span>
                    {m.version === (activeTab === 'selection' ? selectionModels : classifierModels)[0]?.version && (
                      <span className="rounded-full bg-violet-600/20 px-2 py-0.5 text-xs text-violet-400">Terkini</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {m.training_data_size} sampel · {new Date(m.trained_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </p>
                </div>
                <AccuracyBadge before={m.accuracy_before} after={m.accuracy_after} />
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div className="rounded-xl border border-[#1f1f1f] bg-[#111111] overflow-hidden">
          <div className="border-b border-[#1f1f1f] px-5 py-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-400" />
            <h2 className="text-sm font-semibold text-white">Rekomendasi Influencer AI</h2>
          </div>
          <div className="divide-y divide-[#1f1f1f]">
            {isLoading && Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse bg-[#0d0d0d] m-3 rounded-lg" />
            ))}
            {!isLoading && recommendations.length === 0 && (
              <div className="p-8 text-center">
                <TrendingUp className="h-10 w-10 text-gray-700 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Belum ada rekomendasi</p>
                <p className="text-gray-600 text-xs mt-1">Selesaikan kampanye untuk melatih model AI</p>
              </div>
            )}
            {!isLoading && recommendations.map((r, i) => (
              <div key={r.influencer_id} className="px-5 py-3 hover:bg-[#0d0d0d] transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs text-gray-600 w-5 shrink-0">#{i + 1}</span>
                    <div className="min-w-0">
                      <p className="text-white text-sm font-medium truncate font-mono">{r.influencer_id}</p>
                      <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                        <span>Konversi: <span className="text-green-400">{(r.predicted_conversion_rate * 100).toFixed(1)}%</span></span>
                        <span>GMV: <span className="text-white">Rp {(r.predicted_gmv / 1_000_000).toFixed(1)}M</span></span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-2">
                  <p className="text-xs text-gray-600 mb-1">Confidence</p>
                  <ConfidenceBar value={r.confidence_score} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
