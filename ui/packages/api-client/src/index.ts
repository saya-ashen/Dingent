import { createHttp } from "./http";
import { createAuthApi } from "./auth";
import { createDashboardApi } from "./dashboard";
import type { ApiClientConfig } from "./config";

export * from "./types";


export function createApiClient(cfg: ApiClientConfig) {
  const http = createHttp(cfg);

  // 2. Pass the http instance to your API modules.
  //    No more tokenStore!
  return {
    auth: createAuthApi(http, { authPath: "/auth" }),
    dashboard: createDashboardApi(http, "/dashboard"),
  };
}

export const api = createApiClient({ baseURL: "/api/v1" });
export type { DashboardApi } from "./dashboard";

