import { NextRequest, NextResponse } from "next/server";

export const dynamic = 'force-dynamic';

// 你的 Python 后端地址
const API_BASE = process.env.API_BASE || "http://localhost:8000";

// 定义 Next.js 捕获的参数类型
type Params = { path: string[] };

/**
 * 通用代理函数：透明转发
 */
async function proxy(req: NextRequest, context: { params: Promise<Params> }) {
  const { path } = await context.params;

  const pathString = path?.join("/") ?? "";

  const targetUrl = new URL(`${API_BASE}/api/v1/${pathString}`);

  // 3. 复制查询参数 (?page=1&limit=10)
  targetUrl.search = req.nextUrl.search;


  // 4. 处理 Headers
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.set('X-Forwarded-Host', req.headers.get('host') || '');
  headers.set('X-Forwarded-Proto', req.nextUrl.protocol.replace(':', ''));

  try {
    const resp = await fetch(targetUrl.toString(), {
      method: req.method,
      headers,
      body: req.body, // POST/PUT body 透传
      redirect: "manual",
      cache: "no-store",
      // @ts-expect-error - duplex needed for streaming
      duplex: "half",
    });

    return new NextResponse(resp.body, {
      status: resp.status,
      statusText: resp.statusText,
      headers: resp.headers,
    });
  } catch (error) {
    console.error("[Proxy Error]", error);
    return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
  }
}

// 导出所有 HTTP 方法
export async function GET(req: NextRequest, ctx: any) { return proxy(req, ctx); }
export async function POST(req: NextRequest, ctx: any) { return proxy(req, ctx); }
export async function PUT(req: NextRequest, ctx: any) { return proxy(req, ctx); }
export async function PATCH(req: NextRequest, ctx: any) { return proxy(req, ctx); }
export async function DELETE(req: NextRequest, ctx: any) { return proxy(req, ctx); }
export async function OPTIONS(req: NextRequest, ctx: any) { return proxy(req, ctx); }
