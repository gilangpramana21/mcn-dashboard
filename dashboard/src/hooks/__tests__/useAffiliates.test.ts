// Feature: influencer-dashboard-ui, Property 9: Filter influencer selalu menghasilkan query parameter yang konsisten

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { buildAffiliateQueryParams } from '../useAffiliates'
import type { InfluencerFilters } from '@/types/api'

/**
 * Validates: Requirements 3.5
 *
 * Property 9: Filter influencer selalu menghasilkan query parameter yang konsisten
 */

// Arbitrary untuk InfluencerFilters
const influencerFiltersArb = fc.record({
  page: fc.integer({ min: 1, max: 1000 }),
  page_size: fc.integer({ min: 1, max: 100 }),
  min_followers: fc.option(fc.integer({ min: 0, max: 10_000_000 }), { nil: undefined }),
  max_followers: fc.option(fc.integer({ min: 0, max: 10_000_000 }), { nil: undefined }),
  min_engagement_rate: fc.option(fc.float({ min: 0, max: 100 }), { nil: undefined }),
  categories: fc.option(
    fc.array(fc.string({ minLength: 1, maxLength: 20 }), { maxLength: 5 }),
    { nil: undefined }
  ),
  locations: fc.option(
    fc.array(fc.string({ minLength: 1, maxLength: 20 }), { maxLength: 5 }),
    { nil: undefined }
  ),
}) as fc.Arbitrary<InfluencerFilters>

describe('buildAffiliateQueryParams', () => {
  it('Property 9a: determinism — input yang sama selalu menghasilkan output yang sama', () => {
    fc.assert(
      fc.property(influencerFiltersArb, (filters) => {
        const result1 = buildAffiliateQueryParams(filters)
        const result2 = buildAffiliateQueryParams(filters)
        expect(result1).toEqual(result2)
      }),
      { numRuns: 100 }
    )
  })

  it('Property 9b: page dan page_size selalu ada dalam output', () => {
    fc.assert(
      fc.property(influencerFiltersArb, (filters) => {
        const result = buildAffiliateQueryParams(filters)
        expect(result).toHaveProperty('page')
        expect(result).toHaveProperty('page_size')
        expect(result.page).toBe(String(filters.page))
        expect(result.page_size).toBe(String(filters.page_size))
      }),
      { numRuns: 100 }
    )
  })

  it('Property 9c: field opsional hanya muncul di output jika didefinisikan di input', () => {
    fc.assert(
      fc.property(influencerFiltersArb, (filters) => {
        const result = buildAffiliateQueryParams(filters)

        // min_followers hanya ada jika didefinisikan
        if (filters.min_followers == null) {
          expect(result).not.toHaveProperty('min_followers')
        } else {
          expect(result).toHaveProperty('min_followers', String(filters.min_followers))
        }

        // max_followers hanya ada jika didefinisikan
        if (filters.max_followers == null) {
          expect(result).not.toHaveProperty('max_followers')
        } else {
          expect(result).toHaveProperty('max_followers', String(filters.max_followers))
        }

        // min_engagement_rate hanya ada jika didefinisikan
        if (filters.min_engagement_rate == null) {
          expect(result).not.toHaveProperty('min_engagement_rate')
        } else {
          expect(result).toHaveProperty('min_engagement_rate', String(filters.min_engagement_rate))
        }

        // categories hanya ada jika array non-kosong
        if (!filters.categories?.length) {
          expect(result).not.toHaveProperty('categories')
        } else {
          expect(result).toHaveProperty('categories', filters.categories.join(','))
        }

        // locations hanya ada jika array non-kosong
        if (!filters.locations?.length) {
          expect(result).not.toHaveProperty('locations')
        } else {
          expect(result).toHaveProperty('locations', filters.locations.join(','))
        }
      }),
      { numRuns: 100 }
    )
  })
})
