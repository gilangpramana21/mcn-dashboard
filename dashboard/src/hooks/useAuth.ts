'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { getToken, setToken, removeToken } from '@/lib/auth'
import type { LoginResponse } from '@/types/api'

function getRoleFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.role ?? null
  } catch {
    return null
  }
}

export function useAuth() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [role, setRole] = useState<string | null>(null)

  // Baca role dari token hanya di client side (hindari hydration mismatch)
  useEffect(() => {
    const token = getToken()
    if (token) {
      setRole(getRoleFromToken(token))
    }
  }, [])

  const isAdmin = role === 'Administrator'
  const isManager = role === 'Manajer_Kampanye' || isAdmin
  const isReviewer = role === 'Peninjau'

  async function login(username: string, password: string) {
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.post<LoginResponse>('/auth/login', {
        username,
        password,
      })
      setToken(data.access_token)
      setRole(getRoleFromToken(data.access_token))
      router.push('/')
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('Username atau kata sandi tidak valid')
      } else {
        setError('Terjadi kesalahan. Silakan coba lagi.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  async function register(username: string, password: string, confirmPassword: string) {
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.post<LoginResponse>('/auth/register', {
        username,
        password,
        confirm_password: confirmPassword,
      })
      setToken(data.access_token)
      setRole(getRoleFromToken(data.access_token))
      router.push('/')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409) {
        setError('Username sudah digunakan.')
      } else if (err?.response?.status === 400 && detail) {
        setError(typeof detail === 'string' ? detail : 'Data tidak valid.')
      } else {
        setError('Terjadi kesalahan. Silakan coba lagi.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  async function logout() {
    try {
      await apiClient.post('/auth/logout')
    } catch {
      // ignore
    } finally {
      removeToken()
      setRole(null)
      router.push('/login')
    }
  }

  return { login, logout, register, isLoading, error, role, isAdmin, isManager, isReviewer }
}
