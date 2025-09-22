import { createHttp } from "./http";
import { createBrowserTokenStorage, createMemoryTokenStorage } from "./storage";
import { createAuthApi } from "./auth";
import { createDashboardApi } from "./dashboard";
import type { ApiClientConfig } from "./config";

export * from "./types";


export function createApiClient(cfg: ApiClientConfig) {
  const tokenKey = cfg.tokenKey ?? "APP_AUTH_TOKEN";

  // SSR-safe storage: browser localStorage in client, memory in server
  const tokenStore =
    typeof window === "undefined"
      ? createMemoryTokenStorage()
      : createBrowserTokenStorage(tokenKey);
  const http = createHttp(cfg, tokenStore);

  return {
    auth: createAuthApi(http, { authPath: "/auth", tokenStore: tokenStore }),
    dashboard: createDashboardApi(http, "/dashboard"),
  };
}

export const api = createApiClient({ baseURL: "/api/v1" });
export type { DashboardApi } from "./dashboard";

