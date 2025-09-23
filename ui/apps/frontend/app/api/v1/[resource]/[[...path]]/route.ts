import { NextRequest, NextResponse } from "next/server";

export const dynamic = 'force-dynamic';

const FRONTEND_BASE = "frontend";
const DASHBOARD_BASE = "dashboard";
const API_BASE = process.env.API_BASE || "http://localhost:8000";

type Params = { resource: string; path?: string[] };

// Resource -> Backend mapping
const RESOURCE_TO_BACKEND: Record<string, string> = {
  auth: "",
  session: FRONTEND_BASE,
  config: FRONTEND_BASE,
  users: DASHBOARD_BASE,
  projects: DASHBOARD_BASE,
  reports: DASHBOARD_BASE,
  files: DASHBOARD_BASE,
  overview: DASHBOARD_BASE,
  assistants: DASHBOARD_BASE,
  workflows: DASHBOARD_BASE,
  plugins: DASHBOARD_BASE,
  market: DASHBOARD_BASE,
  settings: DASHBOARD_BASE,
  logs: DASHBOARD_BASE,
};


export async function GET(req: NextRequest, context: { params: Promise<Params> }) {
  return proxy(req, context.params);
}
export async function POST(req: NextRequest, context: { params: Promise<Params> }) {
  return proxy(req, context.params);
}
export async function PUT(req: NextRequest, context: { params: Promise<Params> }) {
  return proxy(req, context.params);
}
export async function PATCH(req: NextRequest, context: { params: Promise<Params> }) {
  return proxy(req, context.params);
}
export async function DELETE(req: NextRequest, context: { params: Promise<Params> }) {
  return proxy(req, context.params);
}
export async function OPTIONS(req: NextRequest, context: { params: Promise<Params> }) {
  return proxy(req, context.params);
}

async function proxy(req: NextRequest, params: Promise<Params>) {
  const { resource, path: rest } = await params;
  const backend = RESOURCE_TO_BACKEND[resource] ?? "";

  const sub = rest?.join("/") ?? "";
  const url = req.nextUrl.clone();
  const targetUrl = new URL(
    [API_BASE, "api", "v1", backend, resource, sub].filter(Boolean).join("/")
  );
  targetUrl.search = url.search;


  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.set('X-Forwarded-Host', req.headers.get('host') || '');
  headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

  const resp = await fetch(targetUrl.toString(), {
    method: req.method,
    headers,
    body: req.body,
    redirect: "manual",
    cache: "no-store",
    // @ts-expect-error - duplex is needed for streaming request bodies
    duplex: "half",
  });

  return new NextResponse(resp.body, {
    status: resp.status,
    statusText: resp.statusText,
    headers: resp.headers,
  });
}
