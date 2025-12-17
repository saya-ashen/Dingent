import {
  copilotRuntimeNextJSAppRouterEndpoint,
  CopilotRuntime,
  LangGraphAgent,
  ExperimentalEmptyAdapter,
} from "@copilotkit/runtime";
import { type NextRequest } from "next/server";
import { cookies } from "next/headers"; // 1. 引入 cookies

const serviceAdapter = new ExperimentalEmptyAdapter();

const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
const logLevel = process.env.NODE_ENV === "development" ? "debug" : undefined;

export const POST = async (
  req: NextRequest,
  context: { params: { slug: string } },
) => {
  const { slug } = context.params;

  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) { return new Response("Unauthorized", { status: 401 }); }

  const runtime = new CopilotRuntime({
    agents: {
      [slug]: new LangGraphAgent({
        deploymentUrl: `${backendUrl}/api/v1/${slug}/chat`,
        graphId: slug,

        propertyHeaders: {
          Authorization: `Bearer ${token}`
        }
      }),
    },
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: `/api/v1/${slug}/chat`,
    logLevel,
  });

  return handleRequest(req);
};

export const OPTIONS = async (
  req: NextRequest,
  context: { params: { slug: string } }
) => {
  // 简单处理 OPTIONS，CopilotKit 内部处理函数通常也能处理
  const runtime = new CopilotRuntime({
    agents: {
      [context.params.slug]: new LangGraphAgent({
        deploymentUrl: `${backendUrl}/api/v1/${context.params.slug}/chat`,
        graphId: context.params.slug,
      }),
    },
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: `/api/v1/${context.params.slug}/chat`,
    logLevel,
  });

  return handleRequest(req);
};
