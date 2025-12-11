import type { AxiosInstance } from "axios";
import { createFrontendApi } from "./frontend";
import { createOverviewApi, createPluginsApi, createSettingsApi, createLogsApi, createMarketApi, createAssistantsApi, createWorkflowsApi } from "./dashboard";

const join = (a: string, b: string) =>
  a.replace(/\/+$/, "") + "/" + b.replace(/^\/+/, "");

export function createWorkspaceScopedApi(http: AxiosInstance, slug: string) {
  const workspaceBase = `/${slug}`;

  const paths = {
    overview: join(workspaceBase, "/overview"),
    assistants: join(workspaceBase, "/assistants"),
    workflows: join(workspaceBase, "/workflows"),
    workspaces: join(workspaceBase, "/workspaces"),
    plugins: join(workspaceBase, "/plugins"),
    market: join(workspaceBase, "/market"),
    logs: join(workspaceBase, "/logs"),
    frontend: join(workspaceBase, "/frontend"),
    agentSettings: join(workspaceBase, "/settings"),
  };

  return {
    overview: createOverviewApi(http, paths.overview),
    assistants: createAssistantsApi(http, paths.assistants),
    workflows: createWorkflowsApi(http, paths.workflows),
    plugins: createPluginsApi(http, paths.plugins),
    market: createMarketApi(http, paths.market),
    logs: createLogsApi(http, paths.logs),
    agentSettings: createSettingsApi(http, paths.agentSettings),
    frontend: createFrontendApi(http, paths.frontend),
  };
}

export type WorkspaceScopedApi = ReturnType<typeof createWorkspaceScopedApi>;
