'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { Eye, EyeOff, Zap } from 'lucide-react'

export default function LoginPage() {
  const { login, isLoading, error } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await login(username, password)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a] px-4">
      <div className="w-full max-w-sm space-y-6 rounded-xl border border-[#1f1f1f] bg-[#111111] p-8">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="text-base font-semibold text-white">MCN Dashboard</span>
        </div>

        <div>
          <h1 className="text-xl font-semibold text-white">Masuk ke Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Selamat datang kembali</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoComplete="username"
              placeholder="Masukkan username"
              className="mt-1 w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none transition-colors"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400">Kata Sandi</label>
            <div className="relative mt-1">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="Masukkan kata sandi"
                className="w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 pr-10 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-300"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {error && (
            <p role="alert" className="rounded-lg bg-red-900/20 border border-red-900/30 px-3 py-2 text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-violet-600 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Memuat...' : 'Masuk'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500">
          Belum punya akun?{' '}
          <Link href="/register" className="text-violet-400 hover:text-violet-300 transition-colors">
            Daftar sekarang
          </Link>
        </p>
      </div>
    </div>
  )
}
