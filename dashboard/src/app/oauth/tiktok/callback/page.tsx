'use client'
import { useEffect, useState } from 'react'
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

export default function TikTokOAuthCallback() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code') || params.get('auth_code')
    const error = params.get('error')

    if (error) {
      setStatus('error')
      setMessage(`TikTok menolak authorize: ${error}`)
      return
    }

    if (!code) {
      setStatus('error')
      setMessage('Tidak ada auth code dari TikTok.')
      return
    }

    apiClient.post('/tiktok-shop/oauth/callback', { auth_code: code })
      .then(() => {
        setStatus('success')
        setMessage('Berhasil! Token tersimpan. Halaman ini akan tertutup otomatis.')
        setTimeout(() => window.close(), 2000)
      })
      .catch(e => {
        setStatus('error')
        setMessage(e?.response?.data?.detail ?? 'Gagal menyimpan token.')
      })
  }, [])

  return (
    <div className="min-h-screen bg-[#0d0d0d] flex items-center justify-center p-6">
      <div className="text-center space-y-4">
        {status === 'loading' && (
          <>
            <Loader2 className="h-10 w-10 text-violet-400 animate-spin mx-auto" />
            <p className="text-white">Memproses authorization...</p>
          </>
        )}
        {status === 'success' && (
          <>
            <CheckCircle className="h-10 w-10 text-green-400 mx-auto" />
            <p className="text-white font-medium">Berhasil terhubung!</p>
            <p className="text-sm text-gray-500">{message}</p>
          </>
        )}
        {status === 'error' && (
          <>
            <AlertCircle className="h-10 w-10 text-red-400 mx-auto" />
            <p className="text-white font-medium">Gagal</p>
            <p className="text-sm text-gray-500">{message}</p>
            <button onClick={() => window.close()} className="text-xs text-violet-400 hover:text-violet-300">
              Tutup
            </button>
          </>
        )}
      </div>
    </div>
  )
}
