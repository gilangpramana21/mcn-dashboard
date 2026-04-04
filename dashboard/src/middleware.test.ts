import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { shouldRedirectToLogin } from './middleware'

// Feature: influencer-dashboard-ui, Property 2: Redirect ke login saat tidak terautentikasi

describe('middleware - shouldRedirectToLogin', () => {
  it('should redirect when no token and path is not /login or /api', () => {
    expect(shouldRedirectToLogin('/dashboard', false)).toBe(true)
    expect(shouldRedirectToLogin('/', false)).toBe(true)
    expect(shouldRedirectToLogin('/influencers', false)).toBe(true)
  })

  it('should not redirect when token is present', () => {
    expect(shouldRedirectToLogin('/dashboard', true)).toBe(false)
    expect(shouldRedirectToLogin('/', true)).toBe(false)
  })

  it('should not redirect for /login route even without token', () => {
    expect(shouldRedirectToLogin('/login', false)).toBe(false)
  })

  it('should not redirect for /api routes even without token', () => {
    expect(shouldRedirectToLogin('/api/v1/auth/login', false)).toBe(false)
  })

  describe('Property 2: Redirect ke login saat tidak terautentikasi', () => {
    it('redirects to login for any non-auth, non-api path without a token', () => {
      // Validates: Persyaratan 1.1
      fc.assert(
        fc.property(
          fc.webPath().filter(
            (p) => !p.startsWith('/login') && !p.startsWith('/api')
          ),
          (pathname) => {
            return shouldRedirectToLogin(pathname, false) === true
          }
        ),
        { numRuns: 100 }
      )
    })

    it('never redirects when token is present, regardless of path', () => {
      fc.assert(
        fc.property(
          fc.webPath(),
          (pathname) => {
            return shouldRedirectToLogin(pathname, true) === false
          }
        ),
        { numRuns: 100 }
      )
    })

    it('never redirects for /login paths regardless of token', () => {
      fc.assert(
        fc.property(
          fc.boolean(),
          (hasToken) => {
            return shouldRedirectToLogin('/login', hasToken) === false
          }
        ),
        { numRuns: 100 }
      )
    })

    it('never redirects for /api paths regardless of token', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 0, maxLength: 50 }).map((s) => `/api/${s}`),
          fc.boolean(),
          (pathname, hasToken) => {
            return shouldRedirectToLogin(pathname, hasToken) === false
          }
        ),
        { numRuns: 100 }
      )
    })
  })
})
