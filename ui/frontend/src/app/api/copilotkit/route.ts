import {
    ExperimentalEmptyAdapter,
    copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";
import { CopilotRuntime, LangGraphAgent } from "@copilotkit/runtime";
const runtime = new CopilotRuntime({
    agents: {
        'sample_agent': new LangGraphAgent({
            deploymentUrl: process.env.DING_BACKEND_URL || 'http://127.0.0.1:8000',
            graphId: 'agent',
        }),
    },
});

const serviceAdapter = new ExperimentalEmptyAdapter();


export const POST = async (req: NextRequest) => {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
        runtime,
        serviceAdapter,
        endpoint: "/api/copilotkit",
        logLevel: "debug",
    });

    return handleRequest(req);
};
