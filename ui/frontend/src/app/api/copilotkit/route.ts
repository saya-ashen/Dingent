import {
    ExperimentalEmptyAdapter,
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
            }),
        },
    });
    logLevel = "debug";
} else {
    // Production environment configuration
    console.log("DINGENT_DEV is not set to true. Running in production mode.");
    runtime = new CopilotRuntime({
        remoteEndpoints: [
            { url: (process.env.DING_BACKEND_URL || "http://localhost:8000") + "/copilotkit" },
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
