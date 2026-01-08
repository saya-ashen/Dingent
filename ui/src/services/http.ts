import axios, { type AxiosInstance } from "axios";
import type { ApiClientConfig } from "./config";

export type TokenProvider = () => string | Promise<string | null> | null;
export type UnauthorizeHandler = () => void;

export interface AuthHooks {
  getAccessToken?: () => string | undefined;
  resetAuthState?: () => void;
}
/**
 * 辅助函数：给任意 Axios 实例绑定 401 拦截器
 */
export function attachAuthInterceptor(
  instance: AxiosInstance,
  onUnauthorized?: UnauthorizeHandler,
) {
  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      // 检查是否是 401 错误，并且是否存在回调函数
      if (err.response?.status === 401 && onUnauthorized) {
        onUnauthorized();
      }
      return Promise.reject(err);
    },
  );
}

export function createHttpClient(
  config: ApiClientConfig,
  onUnauthorized?: UnauthorizeHandler,
): AxiosInstance {
  const instance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeoutMs ?? 120_000,
  });

  attachAuthInterceptor(instance, onUnauthorized);

  return instance;
}
