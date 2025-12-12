import axios, { type AxiosInstance } from "axios";
import type { ApiClientConfig } from "./config";

export type TokenProvider = () => string | Promise<string | null> | null;
export type UnauthorizeHandler = () => void;

export interface AuthHooks {
  getAccessToken?: () => string | undefined;
  resetAuthState?: () => void;
}
type Ref<T> = { current: T };

export function createHttpClient(
  config: ApiClientConfig,
  getToken: TokenProvider,
  onUnauthorized?: UnauthorizeHandler
): AxiosInstance {
  const instance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeoutMs ?? 120_000,
  });

  instance.interceptors.request.use(async (req) => {
    const token = await getToken();
    if (token) {
      req.headers.Authorization = `Bearer ${token}`;
    }

    return req;
  });

  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err.response?.status === 401 && onUnauthorized) {
        onUnauthorized();
      }
      return Promise.reject(err);
    }
  );

  return instance;
}
