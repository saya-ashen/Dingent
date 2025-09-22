import axios, { type AxiosInstance } from "axios";
import type { ApiClientConfig } from "./config";
import type { TokenStorage } from "./storage";
import { toApiError } from "./errors";

export function createHttp(config: ApiClientConfig, tokenStore: TokenStorage): AxiosInstance {
  const instance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeoutMs ?? 120_000,
  });

  instance.interceptors.request.use((req) => {
    const token = tokenStore.get();
    if (token) {
      req.headers = req.headers ?? {};
      (req.headers as any).Authorization = `Bearer ${token}`;
    }
    return req;
  });

  // Optional: unwrap and normalize errors to ApiError at a single place
  instance.interceptors.response.use(
    (resp) => resp,
    (err) => Promise.reject(toApiError(err))
  );

  return instance;
}
