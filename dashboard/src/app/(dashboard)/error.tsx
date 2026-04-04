'use client'

import { useEffect } from 'react'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="text-center space-y-4">
        <p className="text-red-400 text-sm">{error.message || 'Terjadi kesalahan'}</p>
        <button
          onClick={reset}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700"
        >
          Coba lagi
        </button>
      </div>
    </div>
  )
}
