// Feature: influencer-dashboard-ui, Property 7: RankBadge selalu menampilkan warna yang sesuai dengan peringkat
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import * as fc from 'fast-check'
import { RankBadge, getRankBadgeColor } from '../RankBadge'

describe('getRankBadgeColor', () => {
  // Property 7: RankBadge selalu menampilkan warna yang sesuai dengan peringkat
  // Memvalidasi: Persyaratan 8.4
  it('Property 7: selalu mengembalikan warna yang sesuai untuk setiap peringkat positif', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 1000 }),
        (rank) => {
          const colorClass = getRankBadgeColor(rank)
          if (rank <= 3) {
            return colorClass.includes('yellow')
          }
          if (rank <= 10) {
            return colorClass.includes('gray-400') || colorClass.includes('gray-300')
          }
          return colorClass.includes('gray') && colorClass.length > 0
        }
      ),
      { numRuns: 100 }
    )
  })

  it('tidak pernah mengembalikan string kosong untuk peringkat valid', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 1000 }),
        (rank) => {
          const colorClass = getRankBadgeColor(rank)
          return colorClass.length > 0
        }
      ),
      { numRuns: 100 }
    )
  })

  it('rank 1-3 mendapat warna emas (yellow)', () => {
    expect(getRankBadgeColor(1)).toContain('yellow')
    expect(getRankBadgeColor(2)).toContain('yellow')
    expect(getRankBadgeColor(3)).toContain('yellow')
  })

  it('rank 4-10 mendapat warna perak (gray-400)', () => {
    expect(getRankBadgeColor(4)).toContain('gray-4')
    expect(getRankBadgeColor(10)).toContain('gray-4')
  })

  it('rank > 10 mendapat warna abu-abu', () => {
    expect(getRankBadgeColor(11)).toContain('gray')
    expect(getRankBadgeColor(100)).toContain('gray')
  })
})

describe('RankBadge component', () => {
  it('menampilkan nomor peringkat', () => {
    render(<RankBadge rank={5} />)
    expect(screen.getByText('#5')).toBeInTheDocument()
  })

  it('menampilkan badge dengan kelas warna yang benar', () => {
    const { container } = render(<RankBadge rank={1} />)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('yellow')
  })
})
