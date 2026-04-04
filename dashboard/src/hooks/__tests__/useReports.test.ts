// Feature: influencer-dashboard-ui, Property 10: Kalkulasi ROI menghasilkan nilai yang konsisten

import * as fc from 'fast-check'
import { calculateROI } from '../useReports'

/**
 * Validates: Requirements 6.4
 *
 * Property 10: Kalkulasi ROI menghasilkan nilai yang konsisten
 */
describe('calculateROI', () => {
  it('Property 10: hasil selalu finite dan bukan NaN untuk input valid', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(0.01), max: Math.fround(1_000_000) }),  // total_gmv
        fc.float({ min: Math.fround(0.01), max: Math.fround(10_000) }),      // cost_per_conversion
        fc.integer({ min: 1, max: 10_000 }),       // total_influencers
        (gmv, costPerConversion, totalInfluencers) => {
          const roi = calculateROI(gmv, costPerConversion, totalInfluencers)
          return isFinite(roi) && !isNaN(roi)
        }
      ),
      { numRuns: 100 }
    )
  })

  it('Property 10: formula ROI benar = (gmv - cost*influencers) / (cost*influencers) * 100', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(0.01), max: Math.fround(1_000_000) }),
        fc.float({ min: Math.fround(0.01), max: Math.fround(10_000) }),
        fc.integer({ min: 1, max: 10_000 }),
        (gmv, costPerConversion, totalInfluencers) => {
          const roi = calculateROI(gmv, costPerConversion, totalInfluencers)
          const denominator = costPerConversion * totalInfluencers
          const expected = ((gmv - denominator) / denominator) * 100
          return isFinite(expected) ? Math.abs(roi - expected) < 1e-6 : roi === 0
        }
      ),
      { numRuns: 100 }
    )
  })

  it('edge case: denominator 0 mengembalikan 0', () => {
    expect(calculateROI(1000, 0, 5)).toBe(0)
    expect(calculateROI(1000, 5, 0)).toBe(0)
    expect(calculateROI(0, 0, 0)).toBe(0)
  })
})
