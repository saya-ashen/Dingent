import axios, { type AxiosInstance } from "axios";
import type { ApiClientConfig } from "./config";

export type TokenProvider = () => string | Promise<string | null> | null;
export type UnauthorizeHandler = () => void;

export interface AuthHooks {
  getAccessToken?: () => string | undefined;
  resetAuthState?: () => void;
}

export function createHttpClient(
  config: ApiClientConfig,
  onUnauthorized?: UnauthorizeHandler,
): AxiosInstance {
  const instance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeoutMs ?? 120_000,
  });

  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err.response?.status === 401 && onUnauthorized) {
        onUnauthorized();
      }
      return Promise.reject(err);
    },
  );

  return instance;
}
