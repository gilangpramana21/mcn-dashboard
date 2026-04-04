// Feature: influencer-dashboard-ui, Property 8: StatusIndicator selalu menampilkan warna yang sesuai dengan status
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import * as fc from 'fast-check'
import { StatusIndicator, getStatusColor } from '../StatusIndicator'
import type { CampaignStatus } from '@/types/api'

const VALID_STATUSES: CampaignStatus[] = ['ACTIVE', 'DRAFT', 'PAUSED', 'STOPPED', 'COMPLETED']

describe('getStatusColor', () => {
  // Property 8: StatusIndicator selalu menampilkan warna yang sesuai dengan status
  // Memvalidasi: Persyaratan 5.3
  it('Property 8: selalu mengembalikan warna non-empty untuk setiap status valid', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...VALID_STATUSES),
        (status) => {
          const colorClass = getStatusColor(status)
          return colorClass.length > 0
        }
      ),
      { numRuns: 100 }
    )
  })

  it('setiap status mendapat warna yang berbeda', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...VALID_STATUSES),
        fc.constantFrom(...VALID_STATUSES),
        (statusA, statusB) => {
          if (statusA === statusB) return true
          return getStatusColor(statusA) !== getStatusColor(statusB)
        }
      ),
      { numRuns: 100 }
    )
  })

  it('ACTIVE mendapat warna hijau', () => {
    expect(getStatusColor('ACTIVE')).toContain('green')
  })

  it('DRAFT mendapat warna abu-abu', () => {
    expect(getStatusColor('DRAFT')).toContain('gray')
  })

  it('PAUSED mendapat warna kuning', () => {
    expect(getStatusColor('PAUSED')).toContain('yellow')
  })

  it('STOPPED mendapat warna merah', () => {
    expect(getStatusColor('STOPPED')).toContain('red')
  })

  it('COMPLETED mendapat warna biru', () => {
    expect(getStatusColor('COMPLETED')).toContain('blue')
  })
})

describe('StatusIndicator component', () => {
  it('menampilkan label status yang benar', () => {
    render(<StatusIndicator status="ACTIVE" />)
    expect(screen.getByText('Aktif')).toBeInTheDocument()
  })

  it('menampilkan semua status dengan label yang tepat', () => {
    const labels: Record<CampaignStatus, string> = {
      ACTIVE: 'Aktif',
      DRAFT: 'Draft',
      PAUSED: 'Dijeda',
      STOPPED: 'Dihentikan',
      COMPLETED: 'Selesai',
    }

    for (const [status, label] of Object.entries(labels)) {
      const { unmount } = render(<StatusIndicator status={status as CampaignStatus} />)
      expect(screen.getByText(label)).toBeInTheDocument()
      unmount()
    }
  })
})
