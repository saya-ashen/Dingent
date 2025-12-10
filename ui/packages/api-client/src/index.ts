import { createHttp, AuthHooks } from "./http";
import { createAuthApi } from "./auth";
import { createDashboardApi } from "./dashboard";
import type { ApiClientConfig } from "./config";
import { createFrontendApi } from "./frontend";
type Ref<T> = { current: T };

export * from "./types";
const hooksRef: Ref<AuthHooks | undefined> = { current: undefined };


export function createApiClient(cfg: ApiClientConfig) {
  const http = createHttp(cfg, hooksRef);

  return {
    auth: createAuthApi(http, { authPath: "/auth" }),
    dashboard: createDashboardApi(http, "/dashboard"),
    frontend: createFrontendApi(http, "/frontend")
  };
}
export function setAuthHooks(h?: AuthHooks) {
  hooksRef.current = h;
}
export const getBaseUrl = () => {
  if (typeof window !== 'undefined') return '/api/v1/';

  if (process.env.API_BASE_URL) return process.env.API_BASE_URL; // 优先读取环境变量

  return 'http://localhost:3001/api/v1/';
};
export const api = createApiClient({ baseURL: getBaseUrl() });
export type { DashboardApi } from "./dashboard";
