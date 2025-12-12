import {
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
  LangGraphAgent,
  CopilotRuntime,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";



const serviceAdapter = new ExperimentalEmptyAdapter();
export const POST = async (req: NextRequest, { params }: { params: Promise<{ slug: string }> }) => {
  const { slug } = await params;

  if (!slug) {
    return new Response("Missing slug", { status: 400 });
  }

  let runtime: CopilotRuntime;
  let logLevel: "debug" | undefined = undefined;

  runtime = new CopilotRuntime({
    agents: {
      [slug]: new LangGraphAgent({
        deploymentUrl: `http://localhost:8000/api/v1/${slug}/chat`,
        graphId: slug,
      })
    },
  });
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: `/api/v1/${slug}/chat`,
    logLevel: logLevel,
  });

  return handleRequest(req);
};
