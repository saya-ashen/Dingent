import axios, { type AxiosInstance, isAxiosError } from "axios";
import type { ApiClientConfig } from "./config";
import { toApiError } from "./errors";

let isRedirecting = false;

export interface AuthHooks {
  getAccessToken?: () => string | undefined;
  resetAuthState?: () => void;
}

export function createHttp(
  config: ApiClientConfig,
  authHooks?: AuthHooks,
): AxiosInstance {
  const instance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeoutMs ?? 120_000,
  });


  instance.interceptors.request.use((cfg) => {
    const token = authHooks?.getAccessToken?.();
    if (token) {
      cfg.headers.Authorization = `Bearer ${token}`;
    }
    return cfg;
  });

  instance.interceptors.response.use(
    (resp) => resp,
    (err) => {
      if (isAxiosError(err) && err.response?.status === 401) {
        if (typeof window !== "undefined" && !isRedirecting) {
          isRedirecting = true;
          authHooks?.resetAuthState?.();

          const next = encodeURIComponent(window.location.pathname + window.location.search);
          window.location.href = `/auth/login?next=${next}`;
          return new Promise(() => { });
        }
      }

      return Promise.reject(toApiError(err));
    }
  );

  return instance;
}


