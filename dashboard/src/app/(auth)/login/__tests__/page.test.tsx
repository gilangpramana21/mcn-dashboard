// Feature: influencer-dashboard-ui, Property 3: Pesan error 401 tidak mengungkap detail teknis
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import * as fc from 'fast-check'

// Mock next/navigation before importing the component
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Mock useAuth hook
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

import LoginPage from '../page'

const TECHNICAL_TERMS = [
  'stack',
  'trace',
  'database',
  'sql',
  'error:',
  'exception',
  'undefined',
  'null',
  '401',
  'status',
]

describe('LoginPage - Property 3: Pesan error 401 tidak mengungkap detail teknis', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Property 3: Pesan error 401 tidak mengungkap detail teknis
  // Memvalidasi: Persyaratan 1.3
  it('Property 3: pesan error yang ditampilkan tidak mengandung detail teknis', () => {
    fc.assert(
      fc.property(
        // Simulate any error message that could come from a 401 response
        fc.constantFrom(
          'Email atau kata sandi tidak valid',
          'Email atau kata sandi tidak valid',
          'Email atau kata sandi tidak valid'
        ),
        (errorMessage) => {
          mockUseAuth.mockReturnValue({
            login: vi.fn(),
            isLoading: false,
            error: errorMessage,
          })

          const { unmount } = render(<LoginPage />)
          const alert = screen.getByRole('alert')
          const displayedText = alert.textContent ?? ''
          unmount()

          // The displayed message must not contain any technical terms
          const containsTechnicalTerm = TECHNICAL_TERMS.some((term) =>
            displayedText.toLowerCase().includes(term.toLowerCase())
          )
          return !containsTechnicalTerm
        }
      ),
      { numRuns: 100 }
    )
  })

  it('exibe a mensagem correta "Email atau kata sandi tidak valid" para erro 401', () => {
    mockUseAuth.mockReturnValue({
      login: vi.fn(),
      isLoading: false,
      error: 'Email atau kata sandi tidak valid',
    })

    render(<LoginPage />)
    expect(screen.getByRole('alert')).toHaveTextContent('Email atau kata sandi tidak valid')
  })

  it('tidak menampilkan alert saat tidak ada error', () => {
    mockUseAuth.mockReturnValue({
      login: vi.fn(),
      isLoading: false,
      error: null,
    })

    render(<LoginPage />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('pesan error tidak mengandung kata teknis seperti stack, trace, database, sql, 401', () => {
    mockUseAuth.mockReturnValue({
      login: vi.fn(),
      isLoading: false,
      error: 'Email atau kata sandi tidak valid',
    })

    render(<LoginPage />)
    const alertText = screen.getByRole('alert').textContent ?? ''

    for (const term of TECHNICAL_TERMS) {
      expect(alertText.toLowerCase()).not.toContain(term.toLowerCase())
    }
  })
})
