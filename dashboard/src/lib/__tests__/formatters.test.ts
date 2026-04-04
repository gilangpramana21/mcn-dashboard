// Feature: influencer-dashboard-ui, Property 5: Format follower count selalu singkat dan valid
// Feature: influencer-dashboard-ui, Property 11: Format engagement rate selalu dua angka desimal
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  formatFollowerCount,
  formatEngagementRate,
  formatCurrency,
  formatDate,
} from '../formatters'

describe('formatFollowerCount', () => {
  // Property 5: Format follower count selalu singkat dan valid
  // Memvalidasi: Persyaratan 8.6
  it('Property 5: selalu menghasilkan string singkat yang valid untuk bilangan bulat positif', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 999_999_999 }),
        (count) => {
          const result = formatFollowerCount(count)
          return (
            result.length > 0 &&
            !result.includes('NaN') &&
            !result.includes('undefined')
          )
        }
      ),
      { numRuns: 100 }
    )
  })

  it('menggunakan satuan K untuk ribuan', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1_000, max: 999_999 }),
        (count) => {
          const result = formatFollowerCount(count)
          return result.endsWith('K')
        }
      ),
      { numRuns: 100 }
    )
  })

  it('menggunakan satuan M untuk jutaan', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1_000_000, max: 999_999_999 }),
        (count) => {
          const result = formatFollowerCount(count)
          return result.endsWith('M')
        }
      ),
      { numRuns: 100 }
    )
  })

  it('contoh spesifik', () => {
    expect(formatFollowerCount(1200)).toBe('1.2K')
    expect(formatFollowerCount(1500000)).toBe('1.5M')
    expect(formatFollowerCount(500)).toBe('500')
    expect(formatFollowerCount(1000)).toBe('1.0K')
  })
})

describe('formatEngagementRate', () => {
  // Property 11: Format engagement rate selalu dua angka desimal
  // Memvalidasi: Persyaratan 8.5
  it('Property 11: selalu menghasilkan string dengan tepat dua angka desimal diikuti %', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 100, noNaN: true }),
        (rate) => {
          const result = formatEngagementRate(rate)
          return /^\d+\.\d{2}%$/.test(result)
        }
      ),
      { numRuns: 100 }
    )
  })

  it('contoh spesifik', () => {
    expect(formatEngagementRate(5.123)).toBe('5.12%')
    expect(formatEngagementRate(0)).toBe('0.00%')
    expect(formatEngagementRate(100)).toBe('100.00%')
    expect(formatEngagementRate(3.5)).toBe('3.50%')
  })
})

describe('formatCurrency', () => {
  it('menghasilkan format IDR yang valid', () => {
    const result = formatCurrency(1500000)
    expect(result).toContain('1.500.000')
    expect(result).toContain('Rp')
  })

  it('tidak pernah menghasilkan NaN atau undefined', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000_000 }),
        (amount) => {
          const result = formatCurrency(amount)
          return result.length > 0 && !result.includes('NaN')
        }
      ),
      { numRuns: 100 }
    )
  })
})

describe('formatDate', () => {
  it('mode daily menghasilkan format tanggal singkat', () => {
    const result = formatDate('2024-01-15', 'daily')
    expect(result).toBeTruthy()
    expect(result.length).toBeGreaterThan(0)
  })

  it('mode monthly menghasilkan bulan dan tahun', () => {
    const result = formatDate('2024-01-15', 'monthly')
    expect(result).toContain('2024')
  })

  it('tanpa mode menghasilkan format lengkap', () => {
    const result = formatDate('2024-01-15')
    expect(result).toBeTruthy()
    expect(result.length).toBeGreaterThan(0)
  })
})
