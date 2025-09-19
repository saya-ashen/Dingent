import {
  ExperimentalEmptyAdapter,
  LangGraphHttpAgent,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";
import { CopilotRuntime, LangGraphAgent } from "@copilotkit/runtime";

let runtime: CopilotRuntime;
let logLevel: "debug" | undefined = undefined;


if (process.env.DINGENT_DEV === 'true') {
  // Development environment configuration
  console.log("DINGENT_DEV is true. Running in development mode.");
  runtime = new CopilotRuntime({
    agents: {
      'dingent': new LangGraphAgent({
        deploymentUrl: process.env.DING_BACKEND_URL || 'http://localhost:8000',
        graphId: 'agent',
        propertyHeaders: {
          Authorization:
            'Bearer <token>',
        },
      }),
    },
  });
  logLevel = "debug";
} else {
  // Production environment configuration
  console.log("DINGENT_DEV is not set to true. Running in production mode.");
  // runtime = new CopilotRuntime({
  //   agents: {
  //
  //     // Our FastAPI endpoint URL
  //     'dingent': new LangGraphHttpAgent({
  //       url: (process.env.DING_BACKEND_URL || "http://127.0.0.1:8000") + "/api/v1/frontend/copilotkit",
  //       headers: { Authorization: req.headers.get("authorization") || "Bearer None" }
  //     }),
  //   },
  // });
  runtime = new CopilotRuntime({
    remoteEndpoints: [
      {
        url: (process.env.DING_BACKEND_URL || "http://localhost:8000") + "/api/v1/frontend/copilotkit",
        onBeforeRequest: ({ ctx }) => {
          return {
            headers: {
              'Authorization': `${ctx.request.headers.get("authorization")}`
            }
          };
        }
      },
    ],
  });

}

const serviceAdapter = new ExperimentalEmptyAdapter();

// Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
    logLevel: logLevel,
  });

  return handleRequest(req);
};
