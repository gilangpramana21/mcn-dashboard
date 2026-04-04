'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { Eye, EyeOff, Zap } from 'lucide-react'

export default function RegisterPage() {
  const { register, isLoading, error } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLocalError(null)

    if (username.length < 3) {
      setLocalError('Username minimal 3 karakter.')
      return
    }
    if (password.length < 8) {
      setLocalError('Password minimal 8 karakter.')
      return
    }
    if (password !== confirmPassword) {
      setLocalError('Password dan konfirmasi password tidak cocok.')
      return
    }

    await register(username, password, confirmPassword)
  }

  const displayError = localError || error

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
          <h1 className="text-xl font-semibold text-white">Buat Akun Baru</h1>
          <p className="text-sm text-gray-500 mt-1">Daftar untuk mengakses dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username */}
          <div>
            <label className="text-sm text-gray-400">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoComplete="username"
              placeholder="Minimal 3 karakter"
              className="mt-1 w-full rounded-lg border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-violet-500 focus:outline-none transition-colors"
            />
          </div>

          {/* Password */}
          <div>
            <label className="text-sm text-gray-400">Password</label>
            <div className="relative mt-1">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Minimal 8 karakter"
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
            {/* Password strength indicator */}
            {password.length > 0 && (
              <div className="mt-1.5 flex gap-1">
                {[1, 2, 3, 4].map(i => (
                  <div
                    key={i}
                    className={`h-1 flex-1 rounded-full transition-colors ${
                      password.length >= i * 3
                        ? password.length >= 12 ? 'bg-green-500' : password.length >= 8 ? 'bg-yellow-500' : 'bg-red-500'
                        : 'bg-[#1f1f1f]'
                    }`}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div>
            <label className="text-sm text-gray-400">Konfirmasi Password</label>
            <div className="relative mt-1">
              <input
                type={showConfirm ? 'text' : 'password'}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Ulangi password"
                className={`w-full rounded-lg border bg-[#0a0a0a] px-3 py-2 pr-10 text-sm text-white placeholder-gray-600 focus:outline-none transition-colors ${
                  confirmPassword && confirmPassword !== password
                    ? 'border-red-500/50 focus:border-red-500'
                    : 'border-[#1f1f1f] focus:border-violet-500'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowConfirm(v => !v)}
                className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-300"
              >
                {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {confirmPassword && confirmPassword !== password && (
              <p className="text-xs text-red-400 mt-1">Password tidak cocok</p>
            )}
          </div>

          {/* Error */}
          {displayError && (
            <p role="alert" className="rounded-lg bg-red-900/20 border border-red-900/30 px-3 py-2 text-sm text-red-400">
              {displayError}
            </p>
          )}

          {/* Info role */}
          <p className="text-xs text-gray-600">
            Akun baru akan mendapat akses sebagai <span className="text-gray-400">Peninjau</span>. Hubungi Administrator untuk upgrade akses.
          </p>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-violet-600 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Mendaftarkan...' : 'Daftar Sekarang'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500">
          Sudah punya akun?{' '}
          <Link href="/login" className="text-violet-400 hover:text-violet-300 transition-colors">
            Masuk di sini
          </Link>
        </p>
      </div>
    </div>
  )
}
