import axios, { type AxiosInstance } from "axios";
import type { ApiClientConfig } from "./config";
import { useAuthStore } from "@repo/store";
import { toApiError } from "./errors";

export function createHttp(config: ApiClientConfig): AxiosInstance {
  const instance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeoutMs ?? 120_000,
  });

  instance.interceptors.request.use((config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Optional: unwrap and normalize errors to ApiError at a single place
  instance.interceptors.response.use(
    (resp) => resp,
    (err) => Promise.reject(toApiError(err))
  );

  return instance;
}
