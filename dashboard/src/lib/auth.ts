const TOKEN_KEY = 'auth_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
  // Set cookie untuk middleware - tanpa HttpOnly agar bisa dibaca JS
  const maxAge = 30 * 60 // 30 menit
  document.cookie = `auth_token=${token}; path=/; max-age=${maxAge}; SameSite=Lax`
}

export function removeToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  // Hapus cookie juga
  document.cookie = 'auth_token=; path=/; max-age=0'
}
