// Feature: influencer-dashboard-ui, Property 6: Sorting tabel membalik arah saat kolom yang sama diklik dua kali

import * as fc from 'fast-check'
import { toggleSortDirection } from '../InfluencerTable'
import type { SortField, SortDirection } from '../InfluencerTable'

/**
 * Validates: Requirements 8.2
 *
 * Property 6: Sorting tabel membalik arah saat kolom yang sama diklik dua kali
 */
describe('InfluencerTable - toggleSortDirection', () => {
  it('Property 6: membalik arah sorting saat kolom yang sama diklik', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<SortField>('follower_count', 'engagement_rate', 'gmv_total'),
        fc.constantFrom<SortDirection>('asc', 'desc'),
        (field, initialDirection) => {
          const newDirection = toggleSortDirection(field, field, initialDirection)
          return newDirection !== initialDirection
        }
      ),
      { numRuns: 100 }
    )
  })

  it('Property 6b: mengatur arah ke desc saat kolom berbeda diklik', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<SortField>('follower_count', 'engagement_rate', 'gmv_total'),
        fc.constantFrom<SortField>('follower_count', 'engagement_rate', 'gmv_total'),
        fc.constantFrom<SortDirection>('asc', 'desc'),
        (clickedField, activeField, currentDirection) => {
          fc.pre(clickedField !== activeField)
          const newDirection = toggleSortDirection(clickedField, activeField, currentDirection)
          return newDirection === 'desc'
        }
      ),
      { numRuns: 100 }
    )
  })
})
