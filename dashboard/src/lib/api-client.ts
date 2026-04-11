import axios from 'axios'
import { toast } from 'sonner'
import { getToken, removeToken } from './auth'

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/backend/api/v1',
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
})

// Request interceptor: tambahkan Authorization header
apiClient.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle error codes
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Jangan redirect otomatis saat login — biarkan caller yang handle
      const isLoginRequest = error.config?.url?.includes('/auth/login')
      if (!isLoginRequest) {
        removeToken()
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
    }
    // Tidak tampilkan toast global untuk 500 atau network error
    // Biarkan masing-masing komponen yang handle error-nya sendiri
    return Promise.reject(error)
  }
)

export { apiClient }

// Helper untuk build request config (digunakan untuk testing)
export function buildRequestConfig(endpoint: string) {
  const token = getToken()
  return {
    url: endpoint,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  }
}
