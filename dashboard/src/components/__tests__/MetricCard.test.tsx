// Feature: influencer-dashboard-ui, Property 4: Skeleton loading ditampilkan saat data dimuat
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import * as fc from 'fast-check'
import { MetricCard } from '../MetricCard'

describe('MetricCard', () => {
  // Property 4: Skeleton loading ditampilkan saat data dimuat
  // Memvalidasi: Persyaratan 2.3, 10.4
  it('Property 4: menampilkan skeleton saat isLoading=true, bukan konten kosong', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        fc.oneof(
          fc.string({ minLength: 1, maxLength: 100 }),
          fc.integer({ min: 0, max: 1_000_000_000 }).map(String)
        ),
        fc.option(fc.string({ minLength: 1, maxLength: 80 }), { nil: undefined }),
        (title, value, subtitle) => {
          const { container, unmount } = render(
            <MetricCard title={title} value={value} subtitle={subtitle} isLoading={true} />
          )
          const skeleton = container.querySelector('[data-testid="metric-skeleton"]')
          // Saat loading, value span (text-2xl) tidak dirender
          const valueSpan = container.querySelector('.text-2xl')
          unmount()
          // Saat loading: skeleton ada, nilai tidak ditampilkan
          return skeleton !== null && valueSpan === null
        }
      ),
      { numRuns: 100 }
    )
  })

  it('menampilkan nilai saat isLoading=false', () => {
    render(<MetricCard title="Total GMV" value="Rp 1.500.000" isLoading={false} />)
    expect(screen.getByText('Rp 1.500.000')).toBeInTheDocument()
    expect(screen.queryByTestId('metric-skeleton')).not.toBeInTheDocument()
  })

  it('menampilkan title selalu', () => {
    render(<MetricCard title="Total Influencer" value={42} isLoading={true} />)
    expect(screen.getByText('Total Influencer')).toBeInTheDocument()
  })

  it('menampilkan subtitle saat tidak loading', () => {
    render(
      <MetricCard
        title="Acceptance Rate"
        value="75%"
        subtitle="rata-rata semua kampanye"
        isLoading={false}
      />
    )
    expect(screen.getByText('rata-rata semua kampanye')).toBeInTheDocument()
  })
})
