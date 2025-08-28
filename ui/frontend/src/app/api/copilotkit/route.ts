import {
    ExperimentalEmptyAdapter,
    copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";
import { CopilotRuntime, LangGraphAgent } from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@ag-ui/langgraph";

let runtime: CopilotRuntime;
let logLevel: "debug" | undefined = undefined;

if (process.env.DINGENT_DEV === 'true') {
    // Development environment configuration
    console.log("DINGENT_DEV is true. Running in development mode.");
    runtime = new CopilotRuntime({
        agents: {
            'sample_agent': new LangGraphAgent({
                deploymentUrl: process.env.DING_BACKEND_URL || 'http://127.0.0.1:8000',
                graphId: 'agent',
            }),
        },
    });
    logLevel = "debug";
} else {
    // Production environment configuration
    console.log("DINGENT_DEV is not set to true. Running in production mode.");
    runtime = new CopilotRuntime({
        agents: {
            "sample_agent": new LangGraphHttpAgent({
                url: process.env.DING_BACKEND_URL || "http://localhost:8000"
            }),
        }
    });
}

const serviceAdapter = new ExperimentalEmptyAdapter();

// Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
        runtime,
        serviceAdapter,
        endpoint: "/api/copilotkit",
        logLevel: logLevel, // This will be "debug" in dev and undefined in prod
    });

    return handleRequest(req);
};
