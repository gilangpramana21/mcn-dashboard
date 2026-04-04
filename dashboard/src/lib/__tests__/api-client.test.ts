// Feature: influencer-dashboard-ui, Property 1: Token disertakan pada setiap request terautentikasi
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'
import { buildRequestConfig } from '../api-client'

describe('API Client - Property 1: Token disertakan pada setiap request terautentikasi', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('Memvalidasi: Persyaratan 1.5 — Authorization header selalu ada saat token tersimpan', () => {
    // Property 1: Token disertakan pada setiap request terautentikasi
    fc.assert(
      fc.property(
        fc.string({ minLength: 10 }), // token
        fc.string({ minLength: 1 }),  // endpoint
        (token, endpoint) => {
          localStorage.setItem('auth_token', token)
          const config = buildRequestConfig(endpoint)
          return config.headers['Authorization'] === `Bearer ${token}`
        }
      ),
      { numRuns: 100 }
    )
  })

  it('Tidak ada Authorization header saat tidak ada token', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        (endpoint) => {
          localStorage.removeItem('auth_token')
          const config = buildRequestConfig(endpoint)
          return !('Authorization' in config.headers)
        }
      ),
      { numRuns: 100 }
    )
  })
})
