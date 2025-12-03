import type { AxiosInstance } from "axios";
import { createOverviewApi } from "./overview";
import { createAssistantsApi } from "./assistants";
import { createWorkflowsApi } from "./workflows";
import { createMarketApi } from "./market";
import { createLogsApi } from "./logs";
import { createSettingsApi } from "./agent-settings";
import { createPluginsApi } from "./plugins";

// 小工具，避免出现 "//" 或漏 "/"
const join = (a: string, b: string) =>
  a.replace(/\/+$/, "") + "/" + b.replace(/^\/+/, "");

export function createDashboardApi(http: AxiosInstance, dashboardBase: string) {
  // 在这里统一定义各子资源的前缀，避免散落在各处
  const paths = {
    overview: join(dashboardBase, "/overview"),
    assistants: join(dashboardBase, "/assistants"),
    workflows: join(dashboardBase, "/workflows"),
    plugins: join(dashboardBase, "/plugins"),
    market: join(dashboardBase, "/market"),
    logs: join(dashboardBase, "/logs"),
    agentSettings: join(dashboardBase, "/settings"),
  };

  return {
    overview: createOverviewApi(http, paths.overview),
    assistants: createAssistantsApi(http, paths.assistants),
    workflows: createWorkflowsApi(http, paths.workflows),
    plugins: createPluginsApi(http, paths.plugins),
    market: createMarketApi(http, paths.market),
    logs: createLogsApi(http, paths.logs),
    agentSettings: createSettingsApi(http, paths.agentSettings),
  };
}

export type DashboardApi = ReturnType<typeof createDashboardApi>;
