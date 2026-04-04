import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Pure function to determine if a redirect to login is needed.
 * Exported for testability.
 */
export function shouldRedirectToLogin(pathname: string, hasToken: boolean): boolean {
  const isAuthRoute = pathname.startsWith('/login')
  const isApiRoute = pathname.startsWith('/api')
  return !isAuthRoute && !isApiRoute && !hasToken
}

// Middleware tidak melakukan redirect auth — ditangani di client-side
// agar tidak ada masalah cookie timing
export function middleware(request: NextRequest) {
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
