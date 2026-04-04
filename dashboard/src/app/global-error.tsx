'use client'

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="id">
      <body style={{ background: '#0a0a0a', color: '#ededed', fontFamily: 'sans-serif' }}>
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <p style={{ color: '#f87171', marginBottom: '1rem' }}>Terjadi kesalahan</p>
            <button
              onClick={reset}
              style={{ background: '#7c3aed', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', border: 'none', cursor: 'pointer' }}
            >
              Coba lagi
            </button>
          </div>
        </div>
      </body>
    </html>
  )
}
