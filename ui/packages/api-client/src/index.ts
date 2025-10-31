import { createHttp, AuthHooks } from "./http";
import { createAuthApi } from "./auth";
import { createDashboardApi } from "./dashboard";
import type { ApiClientConfig } from "./config";
import { createFrontendApi } from "./frontend";

export * from "./types";
let hooks: AuthHooks | undefined;


export function createApiClient(cfg: ApiClientConfig) {
  const http = createHttp(cfg, hooks);

  return {
    auth: createAuthApi(http, { authPath: "/auth" }),
    dashboard: createDashboardApi(http, "/dashboard"),
    frontend: createFrontendApi(http, "/frontend")
  };
}
export function setAuthHooks(h: AuthHooks) { hooks = h; }

export const api = createApiClient({ baseURL: "/api/v1" });
export type { DashboardApi } from "./dashboard";

