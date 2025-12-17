import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // 1. 获取 Cookie
  const token = request.cookies.get('access_token')?.value

  // 2. 准备新的请求头
  const requestHeaders = new Headers(request.headers)

  // 3. 如果 Cookie 存在，将其转换为 Authorization Header
  if (token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  // 4. 继续处理请求（此时请求会进入 rewrites），但带上了新的 Header
  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  })
}

// 5. 匹配路径：只拦截发往 /api/v1/ 的请求
export const config = {
  matcher: '/api/v1/:path*',
}
