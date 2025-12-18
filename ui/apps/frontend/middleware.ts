import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/auth', '/api', '/public']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get('access_token')?.value

  const isPublicPath = PUBLIC_PATHS.some((path) => pathname.startsWith(path))

  if (!token && !isPublicPath) {
    if (pathname.startsWith('/api')) {
      return NextResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      )
    }

    const url = new URL('/auth/login', request.url)
    url.searchParams.set('callbackUrl', pathname)
    return NextResponse.redirect(url)
  }

  const requestHeaders = new Headers(request.headers)

  if (token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  })
}

export const config = {
  // 匹配所有路径，除了静态资源
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
