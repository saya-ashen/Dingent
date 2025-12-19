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
  context: { params: Promise<{ slug?: string }> },
) => {
  const { slug } = await context.params;

  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) { return new Response("Unauthorized", { status: 401 }); }

  const runtime = new CopilotRuntime({
    agents: {
      [slug || "default"]: new LangGraphAgent({
        deploymentUrl: `${backendUrl}/api/v1/${slug}/chat`,
        graphId: slug || "default",

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

