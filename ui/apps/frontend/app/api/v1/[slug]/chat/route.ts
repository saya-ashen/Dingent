class LRUCache<K, V> {
  private max: number;
  private cache: Map<K, V>;

  constructor(max: number) {
    this.max = max;
    this.cache = new Map();
  }

  get(key: K): V | undefined {
    if (!this.cache.has(key)) return undefined;
    const value = this.cache.get(key)!;
    this.cache.delete(key);
    this.cache.set(key, value); // Reinsert to mark as most recently used
    return value;
  }

  set(key: K, value: V): void {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.max) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }
}
import {
  copilotRuntimeNextJSAppRouterEndpoint,
  CopilotRuntime,
  LangGraphAgent,
  ExperimentalEmptyAdapter,
} from "@copilotkit/runtime";
import { type NextRequest } from "next/server";

// This service adapter can be instantiated once as it appears to be stateless.
const serviceAdapter = new ExperimentalEmptyAdapter();

// Cache handlers for each slug to avoid expensive re-instantiation on every request.
const handlerCache = new Map<string, (req: NextRequest, ...args: any[]) => Promise<Response>>();

// Determine settings from environment variables once, with sensible defaults.
const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
const logLevel = process.env.NODE_ENV === "development" ? "debug" : undefined;

function getOrCreateHandler(
  slug: string,
): (req: NextRequest, ...args: any[]) => Promise<Response> {
  // Return cached handler if available
  const cachedHandler = handlerCache.get(slug);
  if (cachedHandler) {
    return cachedHandler;
  }

  // Create a new runtime instance for the specific slug.
  const runtime = new CopilotRuntime({
    agents: {
      [slug]: new LangGraphAgent({
        deploymentUrl: `${backendUrl}/api/v1/${slug}/chat`,
        graphId: slug,
      }),
    },
  });

  // Create the request handler for this specific slug's runtime.
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: `/api/v1/${slug}/chat`,
    logLevel,
  });

  // Cache the newly created handler.
  handlerCache.set(slug, handleRequest as any);
  return handleRequest as any;
}

// The POST handler delegates to the handler factory.
export const POST = (
  req: NextRequest,
  context: { params: { slug: string } },
) => {
  const handler = getOrCreateHandler(context.params.slug);
  return handler(req, context);
};

