import {
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest, NextResponse } from "next/server";
import { CopilotRuntime, LangGraphAgent } from "@copilotkit/runtime";

// --- Environment-based Runtime Configuration ---
let runtime: CopilotRuntime;
let logLevel: "debug" | undefined = undefined;

if (process.env.DINGENT_DEV === 'true') {
  console.log("DINGENT_DEV is true. Running in development mode.");
  runtime = new CopilotRuntime({
    agents: {
      'dingent___': new LangGraphAgent({
        deploymentUrl: process.env.DING_BACKEND_URL || 'http://localhost:8000',
        graphId: 'agent',
        propertyHeaders: {
          Authorization: 'Bearer <token>', // Note: This is for dev only
        },
      }),
    },
  });
  logLevel = "debug";
} else {
  console.log("DINGENT_DEV is not set to true. Running in production mode.");
  runtime = new CopilotRuntime({
    remoteEndpoints: [
      {
        url: (process.env.DING_BACKEND_URL || "http://localhost:8000") + "/api/v1/frontend/copilotkit",
        onBeforeRequest: ({ ctx }) => {
          // Forward the authorization header from the client to the backend agent
          return {
            headers: {
              'Authorization': `${ctx.request.headers.get("authorization")}`
            }
          };
        },

      },

    ],
  });
}

const serviceAdapter = new ExperimentalEmptyAdapter();
export const POST = async (req: NextRequest) => {


  // --- If authentication succeeds, proceed to CopilotKit ---
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/v1/frontend/copilotkit",
    logLevel: logLevel,
  });

  return handleRequest(req);
};
