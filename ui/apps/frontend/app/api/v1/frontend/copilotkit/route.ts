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
const AUTH_VALIDATION_URL = (process.env.DING_BACKEND_URL || "http://localhost:8000") + "/api/v1/auth/verify";

/**
 * Creates a consistent 401 Unauthorized response.
 */
const createUnauthorizedResponse = (req: NextRequest) => {
  const headers = {
    "Content-Type": "application/json",
    // Optional: Standard header indicating what auth scheme is expected
    "WWW-Authenticate": 'Bearer realm="copilotkit", error="invalid_token"',
    // Optional: Custom header for easier frontend detection
    "X-Requires-Auth": "1",
    // Optional: Custom header suggesting a redirect path
    "Location": "/auth/login"
  };
  return new NextResponse(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers });
};

/**
 * Handles POST requests for the CopilotKit runtime, with authentication.
 */
export const POST = async (req: NextRequest) => {
  // --- Authentication Guard ---
  const authorization = req.headers.get("authorization");

  // // 1. Reject if no authorization token is provided.
  // if (!authorization) {
  //   return createUnauthorizedResponse(req);
  // }
  //
  // // 2. Validate the token by calling your backend authentication service.
  // try {
  //   const validationResponse = await fetch(AUTH_VALIDATION_URL, {
  //     method: 'GET',
  //     headers: { 'Authorization': authorization },
  //   });
  //
  //   // If the backend says the token is invalid (e.g., returns 401/403), reject the request.
  //   if (!validationResponse.ok) {
  //     console.log(`Auth validation failed with status: ${validationResponse.status}`);
  //     return createUnauthorizedResponse(req);
  //   }
  // } catch (error) {
  //   console.error("Auth validation request failed:", error);
  //   // If the validation service itself is down or throws an error, return a 500.
  //   return new NextResponse(
  //     JSON.stringify({ error: "Internal Server Error during authentication." }),
  //     { status: 500, headers: { 'Content-Type': 'application/json' } }
  //   );
  // }

  // --- If authentication succeeds, proceed to CopilotKit ---
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/v1/frontend/copilotkit",
    logLevel: logLevel,
  });

  return handleRequest(req);
};
