import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[#0a0a0a] text-center">
      <div className="space-y-2">
        <h1 className="text-6xl font-bold text-white">404</h1>
        <p className="text-lg font-medium text-gray-300">Halaman tidak ditemukan</p>
        <p className="text-sm text-gray-500">
          Halaman yang Anda cari tidak ada atau telah dipindahkan.
        </p>
      </div>
      <Link
        href="/"
        className="rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
      >
        Kembali ke Dashboard
      </Link>
    </div>
  )
}
