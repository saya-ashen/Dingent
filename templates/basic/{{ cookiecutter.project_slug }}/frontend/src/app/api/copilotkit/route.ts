import {
    ExperimentalEmptyAdapter,
    copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";
import { CopilotRuntime, LangGraphAgent } from "@copilotkit/runtime";
const runtime = new CopilotRuntime({
    agents: {
        'sample_agent': new LangGraphAgent({
            deploymentUrl:process.env.BACKEND_API_URL || 'http://127.0.0.1:2024',
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
